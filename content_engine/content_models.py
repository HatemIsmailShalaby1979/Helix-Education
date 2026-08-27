"""Data models for the Content Engine.

Defines the structure of lessons and their constituent sections.
"""

from dataclasses import dataclass, field


@dataclass
class Section:
    """A single lesson section.

    Inputs:
        section_id: Unique identifier for this section.
        title: Human-readable section title.
        body: The section content text (Markdown or plain text).
        source_citations: List of source references supporting this section.
    """

    section_id: str
    title: str
    body: str
    source_citations: list[str] = field(default_factory=list)


@dataclass
class Lesson:
    """A complete lesson for a topic, composed of multiple sections.

    Inputs:
        topic: The topic this lesson belongs to.
        title: Human-readable lesson title.
        sections: Ordered list of Section instances.
        difficulty: Optional difficulty classification.
    """

    topic: str
    title: str
    sections: list[Section] = field(default_factory=list)
    difficulty: str | None = None
