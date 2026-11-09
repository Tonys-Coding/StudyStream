import { FileText } from "lucide-react";
import Tag from "@/components/ui/Tag";

/** The files an answer, plan or quiz was drawn from. Renders nothing if none. */
export default function SourceList({
  sources,
  label = "From",
}: {
  sources: string[] | undefined;
  label?: string;
}) {
  if (!sources || sources.length === 0) return null;

  return (
    <div className="mt-6 flex flex-wrap items-center gap-2 border-t border-rule pt-4">
      <span className="text-meta font-medium text-ink-2">{label}</span>
      {sources.map((source) => (
        <Tag key={source} title={source}>
          <FileText className="size-3.5 shrink-0" aria-hidden />
          <span className="truncate">{source}</span>
        </Tag>
      ))}
    </div>
  );
}
