import { MessageCircleQuestion } from "lucide-react";
import type { FaqResponse } from "@/lib/api";
import Panel from "@/components/ui/Panel";
import SourceList from "./SourceList";

interface Props {
  data: FaqResponse;
  question: string;
}

export default function FaqPanel({ data, question }: Props) {
  return (
    <Panel title="Answer" icon={MessageCircleQuestion}>
      <p className="text-meta font-medium text-ink-2">You asked</p>
      <p className="mt-1 text-body font-medium text-ink">{question}</p>

      <div className="mt-5 border-t border-rule pt-5">
        <p className="prose-read whitespace-pre-wrap text-ink">{data.answer}</p>
      </div>

      <SourceList sources={data.sources} label="Answered from" />

      <p className="mt-6 text-meta text-ink-2">
        Answers come only from your course material. If something looks wrong,
        check with your instructor.
      </p>
    </Panel>
  );
}
