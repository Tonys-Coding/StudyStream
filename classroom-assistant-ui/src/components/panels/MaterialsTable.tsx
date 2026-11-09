import { useState } from "react";
import {
  Check,
  FileText,
  FolderOpen,
  Pencil,
  Trash2,
  Upload,
  X,
} from "lucide-react";
import {
  deleteMaterial,
  fileTypeOf,
  updateMaterialDescription,
  SUPPORTED_EXTENSIONS,
  type Material,
  type Role,
} from "@/lib/api";
import Button, { IconButton } from "@/components/ui/Button";
import EmptyState from "@/components/ui/EmptyState";
import { TextInput } from "@/components/ui/form";
import Notice from "@/components/ui/Notice";
import Panel from "@/components/ui/Panel";
import Skeleton from "@/components/ui/Skeleton";
import { Table, Td, Th } from "@/components/ui/Table";
import Tag from "@/components/ui/Tag";

interface Props {
  courseId: string;
  role: Role | null;
  materials: Material[];
  loading: boolean;
  onUpload: () => void;
  onChanged: () => void;
}

/** The same file name can be a shared file and someone's private copy. */
function keyOf(m: Material): string {
  return `${m.visibility}:${m.source}`;
}

export default function MaterialsTable({
  courseId,
  role,
  materials,
  loading,
  onUpload,
  onChanged,
}: Props) {
  const [editing, setEditing] = useState<string | null>(null);
  const [draft, setDraft] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState("");
  const [confirmingDelete, setConfirmingDelete] = useState<Material | null>(
    null,
  );
  const [deleting, setDeleting] = useState<string | null>(null);

  const isStaff = role === "teacher" || role === "ta";

  // In-progress edits and pending confirmations are cleared by remounting:
  // the caller passes key={courseId}, so switching subjects gives this a
  // fresh state and a confirm can never land on the wrong file.

  async function remove(m: Material) {
    setDeleting(keyOf(m));
    setError("");

    try {
      await deleteMaterial(courseId, m.source, m.visibility);
      setConfirmingDelete(null);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not remove file");
    } finally {
      setDeleting(null);
    }
  }

  function beginEdit(m: Material) {
    setEditing(keyOf(m));
    setDraft(m.description ?? "");
    setError("");
  }

  async function save(m: Material) {
    setSaving(true);
    setError("");

    try {
      await updateMaterialDescription(courseId, m.source, draft, m.visibility);
      setEditing(null);
      onChanged();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not save");
    } finally {
      setSaving(false);
    }
  }

  return (
    <Panel
      title="Course material"
      icon={FolderOpen}
      subtitle={
        isStaff
          ? `Files you upload are shared with everyone in ${courseId}.`
          : "Files you upload are private to you. Files from your teacher are shared with the class."
      }
      actions={
        <Button icon={Upload} onClick={onUpload}>
          Upload
        </Button>
      }
      flush
    >
      <p className="px-5 pt-4 text-meta text-ink-2 md:px-6">
        Supported formats: {SUPPORTED_EXTENSIONS.join(", ")}.
      </p>

      {error && (
        <div className="px-5 pt-4 md:px-6">
          <Notice tone="error">{error}</Notice>
        </div>
      )}

      {loading && (
        <div className="space-y-3 p-5 md:p-6" role="status" aria-label="Loading files">
          <Skeleton className="h-5 w-2/3" />
          <Skeleton className="h-5 w-1/2" />
        </div>
      )}

      {!loading && materials.length === 0 && (
        <div className="p-5 md:p-6">
          <EmptyState
            title={`Nothing uploaded for ${courseId} yet`}
            action={
              <Button variant="primary" icon={Upload} onClick={onUpload}>
                Upload a file
              </Button>
            }
          >
            Add a syllabus, lecture notes or a reading. Study plans, answers
            and quizzes are written from what you upload.
          </EmptyState>
        </div>
      )}

      {!loading && materials.length > 0 && (
        <div className="mt-4 border-t border-rule">
          <Table label="Course material">
            <thead>
              <tr>
                <Th>File</Th>
                <Th>Type</Th>
                <Th>Description</Th>
                <Th className="w-24">
                  <span className="sr-only">Actions</span>
                </Th>
              </tr>
            </thead>

            <tbody>
              {materials.map((m) => {
                const isEditing = editing === keyOf(m);
                const busy = deleting === keyOf(m);

                return (
                  <tr key={keyOf(m)}>
                    <Td>
                      <div className="flex min-w-0 items-center gap-2">
                        <FileText
                          className="size-[18px] shrink-0 text-ink-2"
                          aria-hidden
                        />
                        <span className="truncate font-medium" title={m.source}>
                          {m.source}
                        </span>
                      </div>
                    </Td>

                    <Td>
                      <div className="flex flex-wrap items-center gap-1.5">
                        <Tag>{fileTypeOf(m.source)}</Tag>
                        <Tag tone={m.visibility === "class" ? "mark" : "neutral"}>
                          {m.visibility === "class" ? "Shared" : "Private"}
                        </Tag>
                      </div>
                    </Td>

                    <Td className="min-w-48">
                      {isEditing ? (
                        <div className="flex items-center gap-1">
                          <TextInput
                            autoFocus
                            aria-label={`Description of ${m.source}`}
                            value={draft}
                            onChange={(e) => setDraft(e.target.value)}
                            onKeyDown={(e) => {
                              if (e.key === "Enter") save(m);
                              if (e.key === "Escape") setEditing(null);
                            }}
                            maxLength={140}
                            placeholder="What is this file?"
                            className="h-9"
                          />
                          <IconButton
                            icon={Check}
                            label="Save description"
                            disabled={saving}
                            onClick={() => save(m)}
                          />
                          <IconButton
                            icon={X}
                            label="Cancel"
                            disabled={saving}
                            onClick={() => setEditing(null)}
                          />
                        </div>
                      ) : (
                        <span
                          className={m.description ? "text-ink-2" : "text-ink-3"}
                        >
                          {m.description ||
                            (m.can_edit ? "No description yet" : "No description")}
                        </span>
                      )}
                    </Td>

                    <Td align="right">
                      {m.can_edit && !isEditing && (
                        <div className="flex justify-end gap-0.5">
                          <IconButton
                            icon={Pencil}
                            label={`Edit description of ${m.source}`}
                            onClick={() => beginEdit(m)}
                          />
                          <IconButton
                            icon={Trash2}
                            label={`Remove ${m.source}`}
                            disabled={busy}
                            onClick={() => setConfirmingDelete(m)}
                            className="hover:bg-red-soft hover:text-red"
                          />
                        </div>
                      )}
                    </Td>
                  </tr>
                );
              })}
            </tbody>
          </Table>

          {confirmingDelete && (
            <div className="border-t border-rule bg-red-soft/60 px-5 py-4 md:px-6">
              <p className="text-body text-ink">
                Remove <strong>{confirmingDelete.source}</strong> from{" "}
                {courseId}? It will be deleted for good.
              </p>
              <div className="mt-3 flex gap-2">
                <Button
                  variant="danger"
                  size="sm"
                  loading={deleting !== null}
                  onClick={() => remove(confirmingDelete)}
                >
                  Remove file
                </Button>
                <Button
                  size="sm"
                  disabled={deleting !== null}
                  onClick={() => setConfirmingDelete(null)}
                >
                  Keep it
                </Button>
              </div>
            </div>
          )}
        </div>
      )}
    </Panel>
  );
}
