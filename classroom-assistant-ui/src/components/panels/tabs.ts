import {
  BookOpenText,
  ClipboardCheck,
  ListChecks,
  MessageCircleQuestion,
  type LucideIcon,
} from "lucide-react";
import type { AgentSlug } from "@/lib/api";

/** Tab ids. "assessment" is the UI name for the quiz agent. */
export type TabId = "overview" | "study" | "faq" | "assessment";

export interface TabMeta {
  id: TabId;
  label: string;
  icon: LucideIcon;
  /** Which agent fills this tab. Overview is filled by all of them. */
  agent: AgentSlug | null;
}

export const TAB_META: Record<TabId, TabMeta> = {
  overview: { id: "overview", label: "Overview", icon: BookOpenText, agent: null },
  study: { id: "study", label: "Study plan", icon: ListChecks, agent: "study" },
  faq: { id: "faq", label: "Answer", icon: MessageCircleQuestion, agent: "faq" },
  assessment: {
    id: "assessment",
    label: "Practice quiz",
    icon: ClipboardCheck,
    agent: "quiz",
  },
};

export const TAB_ORDER: TabId[] = ["overview", "study", "faq", "assessment"];
