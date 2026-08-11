import { useState } from "react";
import {
  deleteMaterial,
  fileTypeOf,
  updateMaterialDescription,
  SUPPORTED_EXTENSIONS,
  type Material,
} from "@/lib/api";

interface Props {
  courseId: string;
  courseName: string;
  materials: Material[];
  loading: boolean;
  onUpload: () => void;
  onChanged: () => void;
}

const FILE_ICONS: Record<string, string> = {
  PDF: "picture_as_pdf",
  DOCX: "description",
  TXT: "article",
};

function iconFor(source: string): string {
  return FILE_ICONS[fileTypeOf(source)] ?? "draft";
}

export default function MaterialsTable({
  courseId,
  courseName,
  materials,
  loading,
  onUpload,
  onChanged,
}: Props) {
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [confirmingDelete, setConfirmingDelete] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  // In-progress edits and pending confirmations are cleared by remounting:
  // the caller passes key={courseId}, so switching subjects gives this a
  // fresh state and a confirm can never land on the wrong file.

  async function remove(source: string) {
    setDeleting(source);
    setError("");

    try {
      await deleteMaterial(courseId, source);
      setConfirmingDelete(null);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not remove file");
    } finally {
      setDeleting(null);
    }
  }

  function beginEdit(m: Material) {
    setEditing(m.source);
    setDraft(m.description ?? "");
    setError("");
  }

  async function save(source: string) {
    setSaving(true);
    setError("");

    try {
      await updateMaterialDescription(courseId, source, draft);
      setEditing(null);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="paper-card rounded-xl p-8 mt-8">
      <div className="flex items-center justify-between gap-4 flex-wrap mb-1">
        <div className="flex items-center gap-3">
          <span className="material-symbols-outlined filled text-primary text-[28px]">
            folder_open
          </span>
          <h2 className="font-headline-lg text-headline-lg text-on-surface">
            Course Material
          </h2>
        </div>

        <button
          onClick={onUpload}
          className="inline-flex items-center gap-2 px-4 py-2 bg-primary text-on-primary rounded-full font-title-md text-title-md hover:bg-on-primary-fixed-variant transition-colors"
        >
          <span className="material-symbols-outlined text-[20px]">
            upload_file
          </span>
          Upload
        </button>
      </div>

      <p className="text-label-sm text-on-surface-variant mb-6">
        Files {courseName} draws on when answering. Supported formats:{" "}
        {SUPPORTED_EXTENSIONS.join(", ")}
      </p>

      {error && (
        <div className="rounded-xl border border-error/40 bg-error-container/50 p-4 mb-4">
          <p className="text-body-md text-on-error-container">{error}</p>
        </div>
      )}

      {loading && (
        <p className="text-body-md text-on-surface-variant">Loading…</p>
      )}

      {!loading && materials.length === 0 && (
        <div className="rounded-xl border border-chalkboard-border bg-surface-container-low p-5">
          <p className="text-body-md text-on-surface-variant">
            Nothing uploaded for {courseId} yet. Add a syllabus, lecture notes,
            or a reading so this subject can answer questions.
          </p>
        </div>
      )}

      {!loading && materials.length > 0 && (
        <div className="overflow-x-auto">
          <table className="w-full border-collapse">
            <thead>
              <tr className="border-b border-chalkboard-border text-left">
                <th className="pb-3 pr-4 text-label-sm text-on-surface-variant uppercase font-medium">
                  File
                </th>
                <th className="pb-3 pr-4 text-label-sm text-on-surface-variant uppercase font-medium w-20">
                  Type
                </th>
                <th className="pb-3 pr-4 text-label-sm text-on-surface-variant uppercase font-medium">
                  Description
                </th>
                <th className="pb-3 pr-4 text-label-sm text-on-surface-variant uppercase font-medium w-24 text-right">
                  Sections
                </th>
                <th className="pb-3 w-10">
                  <span className="sr-only">Remove</span>
                </th>
              </tr>
            </thead>

            <tbody>
              {materials.map((m) => {
                const isEditing = editing === m.source;

                return (
                  <tr
                    key={m.source}
                    className="border-b border-chalkboard-border/60 align-top"
                  >
                    <td className="py-3 pr-4">
                      <div className="flex items-center gap-2 min-w-0">
                        <span className="material-symbols-outlined text-primary text-[20px] shrink-0">
                          {iconFor(m.source)}
                        </span>
                        <span
                          className="text-body-md text-on-surface truncate"
                          title={m.source}
                        >
                          {m.source}
                        </span>
                      </div>
                    </td>

                    <td className="py-3 pr-4">
                      <span className="px-2 py-0.5 bg-academy-blue-light text-primary rounded-full text-label-sm">
                        {fileTypeOf(m.source)}
                      </span>
                    </td>

                    <td className="py-3 pr-4">
                      {isEditing ? (
                        <div className="flex items-center gap-2">
                          <input
                            autoFocus
                            value={draft}
                            onChange={(e) => setDraft(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") save(m.source);
                              if (e.key === "Escape") setEditing(null);
                            }}
                            maxLength={140}
                            placeholder="What is this file?"
                            className="flex-1 min-w-0 border border-chalkboard-border rounded-lg px-3 py-1.5 text-body-md focus:outline-none focus:border-primary"
                          />
                          <button
                            onClick={() => save(m.source)}
                            disabled={saving}
                            title="Save"
                            className="text-primary p-1 rounded-full hover:bg-surface-container disabled:opacity-40"
                          >
                            <span className="material-symbols-outlined text-[20px]">
                              {saving ? "hourglass_top" : "check"}
                            </span>
                          </button>
                          <button
                            onClick={() => setEditing(null)}
                            disabled={saving}
                            title="Cancel"
                            className="text-on-surface-variant p-1 rounded-full hover:bg-surface-container disabled:opacity-40"
                          >
                            <span className="material-symbols-outlined text-[20px]">
                              close
                            </span>
                          </button>
                        </div>
                      ) : (
                        <button
                          onClick={() => beginEdit(m)}
                          title="Click to edit"
                          className="group flex items-start gap-2 text-left w-full"
                        >
                          <span
                            className={`text-body-md ${
                              m.description
                                ? "text-on-surface-variant"
                                : "text-outline italic"
                            }`}
                          >
                            {m.description || "Add a description"}
                          </span>
                          <span className="material-symbols-outlined text-[16px] text-outline opacity-0 group-hover:opacity-100 transition-opacity shrink-0 mt-0.5">
                            edit
                          </span>
                        </button>
                      )}
                    </td>

                    <td className="py-3 pr-4 text-body-md text-on-surface-variant text-right tabular-nums">
                      {m.chunks}
                    </td>

                    <td className="py-3 text-right">
                      <button
                        onClick={() => setConfirmingDelete(m.source)}
                        disabled={deleting === m.source}
                        title="Remove this file"
                        className="p-1 rounded-full text-on-surface-variant hover:bg-error-container hover:text-error transition-colors disabled:opacity-40"
                      >
                        <span className="material-symbols-outlined text-[20px]">
                          {deleting === m.source ? "hourglass_top" : "delete"}
                        </span>
                      </button>
                    </td>
                  </tr>
                );
              })}

              {confirmingDelete && (
                <tr>
                  <td colSpan={5} className="pt-4">
                    <div className="rounded-xl border border-error/40 bg-error-container/40 p-4 flex items-center justify-between gap-4 flex-wrap">
                      <p className="text-body-md text-on-surface-variant">
                        Remove <strong>{confirmingDelete}</strong> from{" "}
                        {courseId}? Everything indexed from it is deleted and
                        this cannot be undone.
                      </p>
                      <div className="flex gap-2 shrink-0">
                        <button
                          onClick={() => setConfirmingDelete(null)}
                          className="px-4 py-2 rounded-full text-title-md text-on-surface-variant hover:bg-surface-container transition-colors"
                        >
                          Cancel
                        </button>
                        <button
                          onClick={() => remove(confirmingDelete)}
                          disabled={deleting !== null}
                          className="px-4 py-2 rounded-full bg-error text-on-primary text-title-md hover:opacity-90 transition-opacity disabled:opacity-40"
                        >
                          {deleting ? "Removing…" : "Remove"}
                        </button>
                      </div>
                    </div>
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
