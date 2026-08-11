import type { AgentSlug } from "@/lib/api";

/** Tab ids. "assessment" is the UI name for the quiz agent. */
export type TabId = "overview" | "study" | "faq" | "assessment";

export interface TabMeta {
  id: TabId;
  label: string;
  icon: string;
  blurb: string;
  /** Which agent fills this tab. Overview is filled by all of them. */
  agent: AgentSlug | null;
}

export const TAB_META: Record<TabId, TabMeta> = {
  overview: {
    id: "overview",
    label: "Overview",
    icon: "article",
    blurb: "A combined summary of everything produced for your question.",
    agent: null,
  },
  study: {
    id: "study",
    label: "Study & Planning",
    icon: "calendar_month",
    blurb: "A step-by-step plan, focus topics, and an estimated time to spend.",
    agent: "study",
  },
  faq: {
    id: "faq",
    label: "FAQ",
    icon: "quiz",
    blurb: "A direct answer drawn from your course material.",
    agent: "faq",
  },
  assessment: {
    id: "assessment",
    label: "Assessment",
    icon: "assignment",
    blurb: "Practice questions to test yourself against.",
    agent: "quiz",
  },
};

export const TAB_ORDER: TabId[] = ["overview", "study", "faq", "assessment"];
