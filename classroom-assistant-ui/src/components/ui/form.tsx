import { useId, type InputHTMLAttributes, type Ref, type ReactNode, type SelectHTMLAttributes } from "react";
import { cn } from "@/lib/utils";

// One vocabulary for every control, so a sign-up field and the add-subject
// field are recognisably the same thing.
const CONTROL =
  "block w-full h-10 rounded-ctl border border-line bg-sheet px-3 text-body text-ink " +
  "transition-colors duration-150 hover:border-ink-3 disabled:cursor-not-allowed disabled:opacity-50";

export function TextInput({
  className,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { ref?: Ref<HTMLInputElement> }) {
  return <input className={cn(CONTROL, className)} {...props} />;
}

export function Select({
  className,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement>) {
  return <select className={cn(CONTROL, "pr-8", className)} {...props} />;
}

interface FieldProps {
  label: string;
  hint?: string;
  /** Receives the id to put on the control, so the label is attached to it. */
  children: (id: string) => ReactNode;
}

/** A visible label above a control. Placeholders are not labels. */
export function Field({ label, hint, children }: FieldProps) {
  const id = useId();

  return (
    <div>
      <label htmlFor={id} className="mb-1.5 block text-ui font-medium text-ink">
        {label}
      </label>
      {children(id)}
      {hint && <p className="mt-1.5 text-meta text-ink-2">{hint}</p>}
    </div>
  );
}


/** An on/off switch with a label and a line saying what each position does. */
export function Switch({
  checked,
  onChange,
  label,
  hint,
}: {
  checked: boolean;
  onChange: (value: boolean) => void;
  label: string;
  hint: string;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange(!checked)}
      className="flex w-full items-start gap-3 text-left"
    >
      <span
        aria-hidden
        className={cn(
          "mt-0.5 inline-flex h-6 w-11 shrink-0 items-center rounded-full p-0.5 transition-colors duration-150",
          checked ? "bg-hl" : "bg-board-3",
        )}
      >
        <span
          className={cn(
            "size-5 rounded-full bg-chalk shadow transition-transform duration-150",
            checked && "translate-x-5",
          )}
        />
      </span>
      <span className="min-w-0">
        <span className="block text-ui font-medium text-chalk">{label}</span>
        <span className="block text-meta text-chalk-2">{hint}</span>
      </span>
    </button>
  );
}
