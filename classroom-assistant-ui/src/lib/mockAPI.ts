export interface StudyPlanResponse {
  success: boolean;
  study_plan: string[];
  focus_topics: string[];
  estimated_hours: number | null;
}

export async function getStudyPlan(
  courseID: string,
  goal: string,
): Promise<StudyPlanResponse> {
  await new Promise((resolve) => setTimeout(resolve, 800)); // Simulate network latency

  return {
    success: true,
    study_plan: [
      "Review foundational concepts from weeks 1-4, focusing on key readings.",
      "Study weeks 5-8 materials in depth, emphasizing core problem areas.",
      "Practice applying concepts with sample exam questions.",
      "Create summary notes for each topic to aid quick revision.",
    ],
    focus_topics: [
      "Requirements Engineering",
      "System Architecture",
      "Design Patterns",
    ],
    estimated_hours: 8,
  };
}
