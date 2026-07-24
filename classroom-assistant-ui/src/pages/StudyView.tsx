import { useState } from "react";
import { getStudyPlan, type StudyPlanResponse } from "@/lib/mockAPI";

const COURSES = [
  { id: "CS3354", name: "Software Engineering" },
  { id: "HIST2301", name: "World History Since 1500" },
  { id: "BIOL1441", name: "Introduction to Cell Biology" },
  { id: "FIN3320", name: "Principles of Corporate Finance" },
];

export default function StudyView() {
  const [courseId, setCourseId] = useState(COURSES[0].id);
  const [goal, setGoal] = useState("");
  const [result, setResult] = useState<StudyPlanResponse | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleGenerate() {
    if (!goal.trim()) return;
    setLoading(true);
    const response = await getStudyPlan(courseId, goal);
    setResult(response);
    setLoading(false);
  }

  return (
    <div className="max-w-4xl mx-auto p-8">
      <h1 className="font-display text-2xl font-semibold text-primary mb-6">
        StudyStream — Your AI Study Plan Assistant
      </h1>

      <div className="grid grid-cols-[280px_1fr] gap-6">
        <div className="bg-surface border border-border rounded-xl p-5">
          <label className="block text-sm text-on-surface-variant mb-1">
            Course
          </label>
          <select
            className="w-full border border-border rounded-lg px-3 py-2 mb-4"
            value={courseId}
            onChange={(e) => setCourseId(e.target.value)}
          >
            {COURSES.map((c) => (
              <option key={c.id} value={c.id}>
                {c.id} — {c.name}
              </option>
            ))}
          </select>

          <label className="block text-sm text-on-surface-variant mb-1">
            Your goal
          </label>
          <textarea
            className="w-full border border-border rounded-lg px-3 py-2 resize-none"
            rows={4}
            placeholder="Prepare for the midterm"
            value={goal}
            onChange={(e) => setGoal(e.target.value)}
          />

          <button
            onClick={handleGenerate}
            disabled={loading}
            className="w-full mt-4 bg-primary text-white rounded-full py-2.5 font-medium disabled:opacity-50"
          >
            {loading ? "Generating…" : "Generate study plan"}
          </button>
        </div>

        <div className="bg-surface border border-border rounded-xl p-5">
          {!result && (
            <p className="text-on-surface-variant text-sm">
              Fill in a goal and generate your first study plan.
            </p>
          )}

          {result && (
            <>
              <div className="flex gap-3 mb-5">
                <div className="bg-primary-light rounded-lg px-4 py-2 flex-1">
                  <p className="text-xs text-on-surface-variant">
                    Focus topics
                  </p>
                  <p className="font-medium">
                    {result.focus_topics.length} identified
                  </p>
                </div>
                <div className="bg-primary-light rounded-lg px-4 py-2 flex-1">
                  <p className="text-xs text-on-surface-variant">
                    Estimated time
                  </p>
                  <p className="font-medium">{result.estimated_hours} hours</p>
                </div>
              </div>

              <h2 className="font-display font-semibold mb-2">Study plan</h2>
              <div className="space-y-2 mb-5">
                {result.study_plan.map((step, i) => (
                  <div
                    key={i}
                    className="flex gap-3 border border-border rounded-lg p-3"
                  >
                    <span className="bg-primary-light text-primary text-xs font-medium rounded-full w-5 h-5 flex items-center justify-center shrink-0">
                      {i + 1}
                    </span>
                    <p className="font-notebook text-sm">{step}</p>
                  </div>
                ))}
              </div>

              <h2 className="font-display font-semibold mb-2">Focus topics</h2>
              <div className="flex gap-2 flex-wrap">
                {result.focus_topics.map((topic) => (
                  <span
                    key={topic}
                    className="bg-primary-light text-primary text-xs px-3 py-1 rounded-lg"
                  >
                    {topic}
                  </span>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
