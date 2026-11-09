// src/lib/api.ts
import { supabase } from "./supabase";
import type { Course } from "./courses";

const API_BASE =
  import.meta.env.VITE_API_BASE_URL ?? "http://127.0.0.1:8001";

// ---------------------------------------------------------------
// Response shapes
// These mirror the agents' Pydantic models. See API_CONTRACT.md.
// ---------------------------------------------------------------

export interface StudyPlanResponse {
  success: boolean;
  study_plan: string[];
  focus_topics: string[] | null;
  estimated_hours: number | null;
  /** Files the plan drew on, most relevant first. */
  sources: string[];
}

export interface QuizQuestion {
  question: string;
  choices: string[];
  answer: string;
  /** Why the answer is right. May be empty. */
  explanation?: string;
}

export interface QuizResponse {
  success: boolean;
  questions: QuizQuestion[];
  /** Files the questions were written from. */
  sources: string[];
}

export interface FaqResponse {
  success: boolean;
  answer: string;
  /** Files the answer drew on, most relevant first. */
  sources: string[];
}

export type AgentSlug = "study" | "quiz" | "faq";

/** One agent's outcome inside an /ask response. Agents fail independently. */
export type AgentResult<T> =
  | { success: true; response: T }
  | { success: false; message: string };

export interface AskResponse {
  success: boolean;
  query: string;
  overview: string;
  selected_agents: AgentSlug[];
  /** Id of the saved chat, or null if it could not be saved. */
  session_id?: string | null;
  agents: {
    study?: AgentResult<StudyPlanResponse>;
    quiz?: AgentResult<QuizResponse>;
    faq?: AgentResult<FaqResponse>;
  };
}

interface ChatEnvelope<T> {
  success: true;
  agent: AgentSlug;
  response: T;
}

interface ChatRequestBody {
  message: string;
  course_id: string;
  agent: AgentSlug;
  num_questions?: number;
}

// ---------------------------------------------------------------
// Transport
// ---------------------------------------------------------------

export class ApiError extends Error {
  status: number;

  constructor(message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const {
    data: { session },
  } = await supabase.auth.getSession();

  // Fail here rather than sending "Bearer undefined" and reading a 401 back.
  if (!session) {
    throw new ApiError("You are not signed in. Please log in again.", 401);
  }

  let res: Response;

  // The browser has to set Content-Type itself for multipart, so that it can
  // include the boundary. Setting it here would corrupt the upload.
  const isMultipart = options.body instanceof FormData;

  try {
    res = await fetch(`${API_BASE}${path}`, {
      ...options,
      headers: {
        ...(isMultipart ? {} : { "Content-Type": "application/json" }),
        ...options.headers,
        Authorization: `Bearer ${session.access_token}`,
      },
    });
  } catch {
    // fetch only rejects on network-level failures
    throw new ApiError(
      "StudyStream can't connect right now. Check your internet connection and try again.",
      0,
    );
  }

  let body: unknown = null;

  try {
    body = await res.json();
  } catch {
    // fall through to the status-based message below
  }

  if (!res.ok) {
    const message =
      body && typeof body === "object" && "message" in body
        ? String((body as { message: unknown }).message)
        : "Something went wrong. Please try again.";

    throw new ApiError(message, res.status);
  }

  return body as T;
}

async function chat<T>(payload: ChatRequestBody): Promise<T> {
  const envelope = await request<ChatEnvelope<T>>("/chat", {
    method: "POST",
    body: JSON.stringify(payload),
  });

  return envelope.response;
}

// ---------------------------------------------------------------
// Workspace
// One question, fanned out to every relevant agent, plus an overview.
// ---------------------------------------------------------------

export function ask(
  courseId: string,
  message: string,
  numQuestions = 5,
): Promise<AskResponse> {
  return request<AskResponse>("/ask", {
    method: "POST",
    body: JSON.stringify({
      message,
      course_id: courseId,
      num_questions: numQuestions,
    }),
  });
}

// ---------------------------------------------------------------
// Single agent
// Each helper names its agent explicitly, so the orchestrator skips
// selection entirely. Kept for direct, one-agent calls.
// ---------------------------------------------------------------

export function getStudyPlan(
  courseId: string,
  goal: string,
): Promise<StudyPlanResponse> {
  return chat<StudyPlanResponse>({
    message: goal,
    course_id: courseId,
    agent: "study",
  });
}

export function generateQuiz(
  courseId: string,
  topic: string,
  numQuestions = 5,
): Promise<QuizResponse> {
  return chat<QuizResponse>({
    message: topic,
    course_id: courseId,
    agent: "quiz",
    num_questions: numQuestions,
  });
}

export function askFAQ(
  courseId: string,
  question: string,
): Promise<FaqResponse> {
  return chat<FaqResponse>({
    message: question,
    course_id: courseId,
    agent: "faq",
  });
}

// ---------------------------------------------------------------
// Course materials
// ---------------------------------------------------------------

/** Formats the study agent can extract text from. */
export const SUPPORTED_EXTENSIONS = [".txt", ".pdf", ".docx"] as const;

/** Value for an <input type="file"> accept attribute. */
export const UPLOAD_ACCEPT = SUPPORTED_EXTENSIONS.join(",");

export interface Material {
  source: string;
  tag: string;
  chunks: number;
  /** Null until someone writes one, or if the DB column is not added yet. */
  description: string | null;
  /** "class" is shared with everyone in the subject, "private" is yours alone. */
  visibility: Visibility;
  /** True when you uploaded it. */
  mine: boolean;
  /** Whether you may rename, describe or remove it. */
  can_edit: boolean;
}

export type Visibility = "class" | "private";

/** File type label shown in the materials table, e.g. "PDF". */
export function fileTypeOf(source: string): string {
  const ext = source.split(".").pop()?.toUpperCase() ?? "";
  return ext || "FILE";
}

export interface MaterialsResponse {
  success: boolean;
  course_id: string;
  materials: Material[];
}

export interface UploadResponse {
  success: boolean;
  source: string;
  course_id: string;
  chunks: number;
}

export function isSupportedFile(name: string): boolean {
  const lower = name.toLowerCase();
  return SUPPORTED_EXTENSIONS.some((ext) => lower.endsWith(ext));
}

export function listMaterials(courseId: string): Promise<MaterialsResponse> {
  return request<MaterialsResponse>(
    `/materials/${encodeURIComponent(courseId)}`,
  );
}

export function deleteMaterial(
  courseId: string,
  source: string,
  visibility: Visibility,
): Promise<{ success: boolean; source: string; deleted: number }> {
  return request(
    `/materials/${encodeURIComponent(courseId)}?source=${encodeURIComponent(source)}&visibility=${visibility}`,
    { method: "DELETE" },
  );
}

export function updateMaterialDescription(
  courseId: string,
  source: string,
  description: string,
  visibility: Visibility,
): Promise<{ success: boolean; source: string; updated: number }> {
  return request(`/materials/${encodeURIComponent(courseId)}`, {
    method: "PATCH",
    body: JSON.stringify({ source, description, visibility }),
  });
}

export function uploadMaterial(
  courseId: string,
  file: File,
): Promise<UploadResponse> {
  const form = new FormData();
  form.append("course_id", courseId);
  form.append("file", file);

  return request<UploadResponse>("/materials/upload", {
    method: "POST",
    body: form,
  });
}

// ---------------------------------------------------------------
// Profile
// ---------------------------------------------------------------

export type Role = "student" | "teacher" | "ta";

export interface Profile {
  id: string;
  has_profile: boolean;
  role: Role | null;
  full_name: string | null;
}

export function getMe(): Promise<Profile> {
  return request<Profile>("/me");
}

export function setupProfile(
  role: string,
  fullName: string,
  inviteCode?: string,
): Promise<{ success: boolean; role: Role; full_name: string }> {
  return request("/profile/setup", {
    method: "POST",
    body: JSON.stringify({
      role,
      full_name: fullName,
      invite_code: inviteCode || null,
    }),
  });
}

// ---------------------------------------------------------------
// Subjects
// Kept in the database, so they follow you to any browser.
// ---------------------------------------------------------------

export function listCourses(): Promise<{ success: boolean; courses: Course[] }> {
  return request("/courses");
}

export function addCourse(
  id: string,
  name?: string,
  isPublic = false,
): Promise<{ success: boolean; course: Course }> {
  return request("/courses", {
    method: "POST",
    body: JSON.stringify({ id, name: name || null, public: isPublic }),
  });
}

export function leaveCourse(id: string): Promise<{ success: boolean }> {
  return request(`/courses/${encodeURIComponent(id)}`, { method: "DELETE" });
}

// ---------------------------------------------------------------
// Progress
// ---------------------------------------------------------------

export function recordQuiz(
  courseId: string,
  topic: string,
  score: number,
  total: number,
): Promise<{ success: boolean }> {
  return request("/activity/quiz", {
    method: "POST",
    body: JSON.stringify({ course_id: courseId, topic, score, total }),
  });
}

export interface ActivityTotals {
  questions: number;
  quizzes: number;
  /** Null until a quiz has been finished. */
  avg_score_pct: number | null;
}

export interface CourseStats extends ActivityTotals {
  id: string;
  name: string;
  materials: number;
}

export interface ClassStats extends ActivityTotals {
  id: string;
  name: string;
  enrolled: number;
  /** Students who have asked or quizzed at least once. */
  active: number;
}

export interface RecentActivity {
  kind: "ask" | "quiz";
  course_id: string;
  message: string | null;
  score: number | null;
  total: number | null;
  created_at: string;
}

export interface DashboardResponse {
  success: boolean;
  role: Role | null;
  totals: ActivityTotals;
  courses: CourseStats[];
  recent: RecentActivity[];
  /** Teachers and TAs only: counts across everyone in their subjects. */
  class_stats: ClassStats[] | null;
}

export function getDashboard(): Promise<DashboardResponse> {
  return request<DashboardResponse>("/dashboard");
}

// ---------------------------------------------------------------
// Chat sessions
// Every question is kept with its full answer so it can be reopened.
// ---------------------------------------------------------------

export interface SessionSummary {
  id: string;
  title: string;
  created_at: string;
}

export function listSessions(
  courseId: string,
): Promise<{ success: boolean; sessions: SessionSummary[] }> {
  return request(`/sessions?course_id=${encodeURIComponent(courseId)}`);
}

export function getSession(
  id: string,
): Promise<{ success: boolean; session: SessionSummary & { result: AskResponse } }> {
  return request(`/sessions/${encodeURIComponent(id)}`);
}

export function deleteSession(id: string): Promise<{ success: boolean }> {
  return request(`/sessions/${encodeURIComponent(id)}`, { method: "DELETE" });
}

// ---------------------------------------------------------------
// Assignments
// ---------------------------------------------------------------

export interface Assignment {
  id: number;
  course_id: string | null;
  title: string;
  /** YYYY-MM-DD, or null when there is no due date. */
  due_date: string | null;
  done: boolean;
}

export interface AssignmentInput {
  title: string;
  course_id: string | null;
  due_date: string | null;
}

export function listAssignments(): Promise<{
  success: boolean;
  assignments: Assignment[];
}> {
  return request("/assignments");
}

export function addAssignment(
  input: AssignmentInput,
): Promise<{ success: boolean; assignment: Assignment }> {
  return request("/assignments", {
    method: "POST",
    body: JSON.stringify(input),
  });
}

export function updateAssignment(
  id: number,
  changes: Partial<AssignmentInput & { done: boolean }>,
): Promise<{ success: boolean; assignment: Assignment }> {
  return request(`/assignments/${id}`, {
    method: "PATCH",
    body: JSON.stringify(changes),
  });
}

export function deleteAssignment(id: number): Promise<{ success: boolean }> {
  return request(`/assignments/${id}`, { method: "DELETE" });
}

// ---------------------------------------------------------------
// Teachers
// A teacher has a personal code. Students and TAs enter it to see that
// teacher's shared subjects.
// ---------------------------------------------------------------

export interface TeacherSummary {
  id: string;
  full_name: string;
  email: string | null;
  /** The teacher's public subjects. */
  subjects: { id: string; name: string }[];
}

export function listTeachers(): Promise<{
  success: boolean;
  teachers: TeacherSummary[];
}> {
  return request("/teachers");
}

export function linkTeacher(
  code: string,
): Promise<{ success: boolean; teacher: TeacherSummary }> {
  return request("/teachers/link", {
    method: "POST",
    body: JSON.stringify({ code }),
  });
}

export function unlinkTeacher(id: string): Promise<{ success: boolean }> {
  return request(`/teachers/${encodeURIComponent(id)}`, { method: "DELETE" });
}

export interface RosterPerson {
  id: string;
  full_name: string;
  role: Role | null;
  email: string | null;
}

export function getRoster(): Promise<{ success: boolean; people: RosterPerson[] }> {
  return request("/teacher/roster");
}

export function getTeacherCode(): Promise<{
  success: boolean;
  code: string;
  /** How many students and TAs have entered it. */
  students: number;
}> {
  return request("/teacher/code");
}
