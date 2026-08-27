"""Grounding client interface and implementations.

Provides an abstract base class for grounding clients and concrete
implementations: a deterministic stub for testing, an HTTP client for
generic search APIs, and a real web search + extraction client for
authoritative sources.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from urllib.parse import quote_plus

import requests
from bs4 import BeautifulSoup

from .grounding_models import GroundingFetchError, GroundingResult, SourceChunk


class GroundingClient(ABC):
    """Abstract base class for grounding clients.

    All grounding clients must implement the fetch method to retrieve
    source material for a given topic.
    """

    @abstractmethod
    def fetch(self, topic: str, max_chunks: int = 5) -> GroundingResult:
        """Fetch grounding material for a topic.

        Args:
            topic: The topic to search for.
            max_chunks: Maximum number of chunks to return.

        Returns:
            A GroundingResult containing the retrieved chunks.

        Raises:
            GroundingFetchError: If the fetch operation fails.
        """
        pass


class StubGroundingClient(GroundingClient):
    """Deterministic, offline grounding client for testing.

    Returns pre-configured responses for specific topics. Does not make
    any network calls.

    Args:
        canned_responses: Mapping from topic strings to GroundingResult
            objects. Keys are matched exactly against the topic parameter.
        default_response: Optional fallback GroundingResult for topics
            not in canned_responses. If None, unmapped topics raise
            GroundingFetchError.
    """

    def __init__(
        self,
        canned_responses: dict[str, GroundingResult],
        default_response: GroundingResult | None = None,
    ) -> None:
        self._canned = canned_responses
        self._default = default_response

    def fetch(self, topic: str, max_chunks: int = 5) -> GroundingResult:
        """Return canned response for topic or raise if not found."""
        if topic in self._canned:
            result = self._canned[topic]
            # Respect max_chunks by truncating if needed
            if len(result.chunks) > max_chunks:
                return GroundingResult(
                    topic=result.topic,
                    query_used=result.query_used,
                    chunks=result.chunks[:max_chunks],
                    fetched_at=result.fetched_at,
                )
            return result

        if self._default is not None:
            result = self._default
            if len(result.chunks) > max_chunks:
                return GroundingResult(
                    topic=result.topic,
                    query_used=result.query_used,
                    chunks=result.chunks[:max_chunks],
                    fetched_at=result.fetched_at,
                )
            return result

        raise GroundingFetchError(f"No canned response configured for topic: '{topic}'")


@dataclass
class GroundingConfig:
    """Configuration for HttpGroundingClient.

    Args:
        api_url: Base URL of the search API endpoint.
        api_key: Optional API key for authentication (sent as Bearer token).
        timeout_seconds: Request timeout in seconds. Default 15.
    """

    api_url: str
    api_key: str | None = None
    timeout_seconds: int = 15


class HttpGroundingClient(GroundingClient):
    """HTTP-based grounding client using requests library.

    Assumes a generic search API with the following JSON request/response
    shape:

    Request (POST):
        {
            "query": "search query string",
            "max_results": 5
        }

    Response (200 OK):
        {
            "results": [
                {
                    "title": "Source Title",
                    "url": "https://example.com/page",
                    "content": "Full text content or snippet..."
                },
                ...
            ]
        }

    The client sends the topic as the query, splits returned content into
    chunks using the chunker, and returns a GroundingResult.

    Args:
        config: GroundingConfig with api_url, optional api_key, and timeout.
    """

    def __init__(self, config: GroundingConfig) -> None:
        self._config = config
        self._session = requests.Session()
        if config.api_key:
            self._session.headers.update({"Authorization": f"Bearer {config.api_key}"})
        self._session.headers.update({"Content-Type": "application/json"})

    def fetch(self, topic: str, max_chunks: int = 5) -> GroundingResult:
        """Fetch grounding material via HTTP search API.

        Args:
            topic: The topic to search for.
            max_chunks: Maximum number of chunks to return.

        Returns:
            GroundingResult with retrieved and chunked source material.

        Raises:
            GroundingFetchError: On timeout, non-200 response, or parse error.
        """
        from .chunker import split_into_chunks

        payload = {"query": topic, "max_results": max_chunks}

        try:
            response = self._session.post(
                self._config.api_url,
                json=payload,
                timeout=self._config.timeout_seconds,
            )
        except requests.Timeout as e:
            raise GroundingFetchError(f"Request timed out after {self._config.timeout_seconds}s") from e
        except requests.RequestException as e:
            raise GroundingFetchError(f"Network error: {e}") from e

        if response.status_code != 200:
            raise GroundingFetchError(f"API returned {response.status_code}: {response.text[:200]}")

        try:
            data = response.json()
        except ValueError as e:
            raise GroundingFetchError("Response is not valid JSON") from e

        results = data.get("results", [])
        if not isinstance(results, list):
            raise GroundingFetchError("Response 'results' field is not a list")

        all_chunks: list[SourceChunk] = []
        for item in results:
            title = item.get("title", "")
            url = item.get("url", "")
            content = item.get("content", "") or item.get("snippet", "")

            if not title or not url or not content:
                continue

            chunks = split_into_chunks(
                text=content,
                source_url=url,
                source_title=title,
                max_chars=800,
            )
            all_chunks.extend(chunks)
            if len(all_chunks) >= max_chunks:
                break

        return GroundingResult(
            topic=topic,
            query_used=topic,
            chunks=all_chunks[:max_chunks],
        )


def load_grounding_config_from_env() -> GroundingConfig:
    """Build a GroundingConfig from environment variables.

    Reads:
        HELIX_GROUNDING_API_URL (required — raise ValueError with a
          clear message if unset, do not silently default to a fake URL)
        HELIX_GROUNDING_API_KEY (optional, defaults to None)
        HELIX_GROUNDING_TIMEOUT_SECONDS (optional, defaults to 15, must
          parse as int, raise ValueError with a clear message on
          malformed value — do not silently fall back on a parse error)
    Returns:
        A populated GroundingConfig.
    Raises:
        ValueError: if HELIX_GROUNDING_API_URL is unset or empty, or if
          HELIX_GROUNDING_TIMEOUT_SECONDS is set but not a valid integer.
    """
    import os

    # Read and validate HELIX_GROUNDING_API_URL (required)
    api_url = os.environ.get("HELIX_GROUNDING_API_URL")
    if not api_url:
        raise ValueError(
            "HELIX_GROUNDING_API_URL environment variable is required but not set. "
            "Please set it to the base URL of the search API endpoint."
        )

    # Read HELIX_GROUNDING_API_KEY (optional)
    api_key = os.environ.get("HELIX_GROUNDING_API_KEY")

    # Read and validate HELIX_GROUNDING_TIMEOUT_SECONDS (optional)
    timeout_seconds = 15  # Default value
    timeout_env = os.environ.get("HELIX_GROUNDING_TIMEOUT_SECONDS")
    if timeout_env is not None:
        try:
            timeout_seconds = int(timeout_env)
            if timeout_seconds <= 0:
                raise ValueError(f"HELIX_GROUNDING_TIMEOUT_SECONDS must be positive, got {timeout_seconds}")
        except ValueError as e:
            raise ValueError(
                f"HELIX_GROUNDING_TIMEOUT_SECONDS must be a valid integer, got '{timeout_env}'. Error: {e}"
            ) from e

    return GroundingConfig(
        api_url=api_url,
        api_key=api_key,
        timeout_seconds=timeout_seconds,
    )


# ═══════════════════════════════════════════════════════════════════════
# REAL WEB GROUNDING CLIENT — Searches authoritative sources, extracts content
# ═══════════════════════════════════════════════════════════════════════

# Trusted domains for authoritative content (ordered by preference)
AUTHORITATIVE_DOMAINS = [
    # Official documentation
    "docs.python.org",
    "developer.mozilla.org",
    "docs.microsoft.com",
    "docs.aws.amazon.com",
    "cloud.google.com/docs",
    "kubernetes.io/docs",
    "docs.docker.com",
    "terraform.io/docs",
    "react.dev",
    "vuejs.org",
    "angular.io",
    "nextjs.org/docs",
    # Educational / reference
    "realpython.com",
    "python.org",
    "w3schools.com",
    "geeksforgeeks.org",
    "tutorialspoint.com",
    "javatpoint.com",
    "programiz.com",
    # Standards bodies
    "w3.org",
    "ietf.org",
    "iso.org",
    "ecma-international.org",
    # Major tech blogs (high quality)
    "martinfowler.com",
    "microsoft.com/en-us/research",
    "research.google.com",
    "aws.amazon.com/blogs",
    "cloud.google.com/blog",
    "engineering.fb.com",
    "netflixtechblog.com",
    "uber.com/blog",
    "airbnb.io",
    "shopify.engineering",
    "github.blog",
    "gitlab.com/blog",
    # Academic / research
    "arxiv.org",
    "scholar.google.com",
    "doi.org",
    # Q&A (high quality answers)
    "stackoverflow.com",
    "softwareengineering.stackexchange.com",
    "security.stackexchange.com",
]

# Domains to explicitly avoid (low quality, SEO farms, paywalls)
BLOCKED_DOMAINS = [
    "medium.com",
    "dev.to",
    "hashnode.dev",
    "freecodecamp.org",
    "codecademy.com",
    "udemy.com",
    "coursera.org",
    "edx.org",
    "pluralsight.com",
    "linkedin.com",
    "quora.com",
    "reddit.com",
    "pinterest.com",
    "slideshare.net",
    "scribd.com",
    "studocu.com",
    "coursehero.com",
    "chegg.com",
    "brainly.com",
    "studypool.com",
    "nursingessay.org",
    "essaypro.com",
    "paperhelp.org",
    "essayshark.com",
    "edubirdie.com",
    "grademiners.com",
    "speedypaper.com",
    "writepaperfor.me",
    "essayhub.com",
    "myassignmenthelp.com",
    "allassignmenthelp.com",
    "greatassignmenthelp.com",
    "assignmenthelp.net",
    "tophomeworkhelper.com",
    "homeworkhelp.com",
    "studymoose.com",
    "phdessay.com",
    "ivypanda.com",
    "samplius.com",
    "writingbros.com",
    "gradesfixer.com",
    "newyorkessays.com",
    "studydriver.com",
    "paperap.com",
    "freeessaywriter.net",
    "essayzoo.org",
    "123helpme.com",
    "bartleby.com",
    "cliffsnotes.com",
    "sparknotes.com",
    "shmoop.com",
    "enotes.com",
    "gradesaver.com",
    "bookrags.com",
    "novelguide.com",
    "pinkmonkey.com",
    "barronnotes.com",
    "monkeynotes.com",
    "bookwolf.com",
    "literature-study-online.com",
    "thebestnotes.com",
    "monkeynotes.com",
    "booknotes.com",
    "studynotes.org",
    "cram.com",
    "quizlet.com",
    "studystack.com",
    "flashcardmachine.com",
    "brainscape.com",
    "ankiweb.net",
    "memrise.com",
    "duolingo.com",
    "babbel.com",
    "rosettastone.com",
    "busuu.com",
    "lingoda.com",
    "italki.com",
    "preply.com",
    "verbling.com",
    "cambly.com",
    "ef.com",
    "wallstreetenglish.com",
    "britishcouncil.org",
    "cambridgeenglish.org",
    "ielts.org",
    "toefl.org",
    "gre.org",
    "gmat.org",
    "lsat.org",
    "mcat.org",
    "usmle.org",
    "nclex.org",
    "cpaexam.com",
    "cfaexam.com",
    "frm.org",
    "prmia.org",
    "actuary.org",
    "soa.org",
    "casact.org",
    "cia.org",
    "isaca.org",
    "isc2.org",
    "comptia.org",
    "microsoft.com/learn",
    "aws.amazon.com/training",
    "cloud.google.com/training",
    "oracle.com/education",
    "sap.com/training",
    "salesforce.com/trailhead",
    "trailhead.salesforce.com",
    "developer.salesforce.com",
    "developer.mozilla.org/en-US/docs/Learn",
    "web.dev/learn",
    "web.dev",
    "developer.chrome.com",
    "web.dev/blog",
    "chromestatus.com",
    "caniuse.com",
    "html.spec.whatwg.org",
    "dom.spec.whatwg.org",
    "csswg.org",
    "tc39.es",
    "github.com/tc39",
    "github.com/w3c",
    "github.com/whatwg",
]


def _is_authoritative(url: str) -> bool:
    """Check if a URL is from an authoritative domain."""
    from urllib.parse import urlparse

    try:
        domain = urlparse(url).netloc.lower().replace("www.", "")
        # Check blocked first
        for blocked in BLOCKED_DOMAINS:
            if blocked in domain:
                return False
        # Check authoritative
        for auth in AUTHORITATIVE_DOMAINS:
            if auth in domain:
                return True
        return False
    except Exception:
        return False


def _score_url(url: str) -> int:
    """Score a URL for authority (higher = more authoritative)."""
    from urllib.parse import urlparse

    try:
        domain = urlparse(url).netloc.lower().replace("www.", "")
        score = 0
        for i, auth in enumerate(AUTHORITATIVE_DOMAINS):
            if auth in domain:
                score = 1000 - i  # Higher score for earlier in list
                break
        # Boost for HTTPS
        if url.startswith("https://"):
            score += 10
        # Boost for official docs paths
        if any(path in url for path in ["/docs/", "/documentation/", "/reference/", "/guide/", "/tutorial/"]):
            score += 50
        return score
    except Exception:
        return 0


class WebGroundingClient(GroundingClient):
    """Real web grounding client that searches authoritative sources
    and extracts clean content with citations.

    Uses DuckDuckGo HTML scraping (no API key needed) + BeautifulSoup
    for content extraction. Filters for authoritative domains only.
    """

    def __init__(
        self,
        timeout_seconds: int = 20,
        max_results_per_query: int = 10,
        user_agent: str | None = None,
    ) -> None:
        self._timeout = timeout_seconds
        self._max_results = max_results_per_query
        self._session = requests.Session()
        self._session.headers.update(
            {
                "User-Agent": user_agent
                or (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36 HelixEducationBot/1.0"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            }
        )

    def fetch(self, topic: str, max_chunks: int = 5) -> GroundingResult:
        """Search authoritative sources for topic and extract content chunks.

        Args:
            topic: The topic to search for.
            max_chunks: Maximum number of content chunks to return.

        Returns:
            GroundingResult with chunks from authoritative sources.

        Raises:
            GroundingFetchError: If search or extraction fails.
        """

        # Build search queries - try multiple for better coverage
        queries = [
            topic,
            f"{topic} tutorial",
            f"{topic} documentation",
            f"{topic} guide",
            f"how to {topic}",
        ]

        all_chunks: list[SourceChunk] = []
        seen_urls: set[str] = set()

        for query in queries:
            if len(all_chunks) >= max_chunks:
                break

            try:
                urls = self._search_duckduckgo(query)
                # Filter and score URLs
                scored_urls = [(u, _score_url(u)) for u in urls if _is_authoritative(u)]
                scored_urls.sort(key=lambda x: x[1], reverse=True)

                for url, score in scored_urls:
                    if len(all_chunks) >= max_chunks:
                        break
                    if url in seen_urls:
                        continue
                    seen_urls.add(url)

                    try:
                        chunks = self._extract_content(url, max_chunks - len(all_chunks))
                        all_chunks.extend(chunks)
                    except Exception:
                        continue  # Skip failed extractions

            except Exception:
                continue  # Try next query

        if not all_chunks:
            raise GroundingFetchError(
                f"No authoritative content found for topic: '{topic}'. "
                "Try a more specific topic or check network connectivity."
            )

        return GroundingResult(
            topic=topic,
            query_used=queries[0],
            chunks=all_chunks[:max_chunks],
        )

    def _search_duckduckgo(self, query: str) -> list[str]:
        """Search DuckDuckGo and return result URLs."""
        search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        try:
            resp = self._session.get(search_url, timeout=self._timeout)
            resp.raise_for_status()
        except Exception as e:
            raise GroundingFetchError(f"Search request failed: {e}") from e

        soup = BeautifulSoup(resp.text, "html.parser")
        urls = []

        # DuckDuckGo result links
        for link in soup.select("a.result__snippet, a.result__url, .result__title a, .result__snippet a"):
            href = link.get("href")
            if href and href.startswith("http"):
                urls.append(href)

        # Fallback: any result link
        if not urls:
            for link in soup.select(".results a[href^='http']"):
                href = link.get("href")
                if href:
                    urls.append(href)

        # Deduplicate preserving order
        seen = set()
        unique = []
        for u in urls:
            if u not in seen:
                seen.add(u)
                unique.append(u)

        return unique[: self._max_results]

    def _extract_content(self, url: str, max_chunks: int) -> list[SourceChunk]:
        """Extract clean text content from a URL."""
        try:
            resp = self._session.get(url, timeout=self._timeout)
            resp.raise_for_status()
        except Exception as e:
            raise GroundingFetchError(f"Failed to fetch {url}: {e}") from e

        # Detect content type
        content_type = resp.headers.get("Content-Type", "").lower()
        if "pdf" in content_type:
            raise GroundingFetchError("PDF content not supported yet")

        soup = BeautifulSoup(resp.content, "html.parser")

        # Remove noise elements
        for tag in soup(
            [
                "script",
                "style",
                "nav",
                "header",
                "footer",
                "aside",
                "noscript",
                "iframe",
                "form",
                "button",
                "input",
                "select",
                "textarea",
                "svg",
                "path",
                "advertisement",
                "ads",
                ".ad",
                ".ads",
                ".advertisement",
                ".sidebar",
                ".navigation",
                ".menu",
                ".footer",
                ".header",
                "#sidebar",
                "#navigation",
                "#menu",
                "#footer",
                "#header",
                ".cookie",
                ".consent",
                ".popup",
                ".modal",
                ".overlay",
            ]
        ):
            tag.decompose()

        # Try to find main content
        main_content = None
        for selector in [
            "main",
            "article",
            ".content",
            "#content",
            ".main",
            "#main",
            ".post",
            ".article",
            ".entry",
            ".documentation",
            ".docs",
            ".guide-content",
            ".tutorial-content",
            ".reference-content",
            "[role='main']",
            ".markdown-body",
            ".prose",
        ]:
            main_content = soup.select_one(selector)
            if main_content:
                break

        if not main_content:
            main_content = soup.body or soup

        # Extract text
        text = main_content.get_text(separator="\n", strip=True)

        # Clean up
        lines = [line.strip() for line in text.split("\n") if line.strip()]
        text = "\n".join(lines)

        # Truncate if too long
        if len(text) > 15000:
            text = text[:15000] + "..."

        if len(text) < 200:
            raise GroundingFetchError(f"Content too short from {url}")

        # Get title
        title_tag = soup.find("title")
        title = title_tag.get_text(strip=True) if title_tag else url

        # Chunk the content
        from .chunker import split_into_chunks

        chunks = split_into_chunks(
            text=text,
            source_url=url,
            source_title=title,
            max_chars=1200,
        )

        return chunks[:max_chunks]
