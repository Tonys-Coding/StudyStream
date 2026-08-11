// src/lib/api.ts
import { supabase } from "./supabase";

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
}

export interface QuizQuestion {
  question: string;
  choices: string[];
  answer: string;
}

export interface QuizResponse {
  success: boolean;
  questions: QuizQuestion[];
}

export interface FaqResponse {
  success: boolean;
  answer: string;
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
      `Could not reach the server at ${API_BASE}. Is the backend running?`,
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
        : `Request failed with status ${res.status}`;

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
}

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

export interface CoursesResponse {
  success: boolean;
  courses: { course_id: string; chunks: number }[];
}

/** Courses that already have material ingested, regardless of local list. */
export function listCourses(): Promise<CoursesResponse> {
  return request<CoursesResponse>("/courses");
}

export function deleteMaterial(
  courseId: string,
  source: string,
): Promise<{ success: boolean; source: string; deleted: number }> {
  return request(
    `/materials/${encodeURIComponent(courseId)}?source=${encodeURIComponent(source)}`,
    { method: "DELETE" },
  );
}

export function updateMaterialDescription(
  courseId: string,
  source: string,
  description: string,
): Promise<{ success: boolean; source: string; updated: number }> {
  return request(`/materials/${encodeURIComponent(courseId)}`, {
    method: "PATCH",
    body: JSON.stringify({ source, description }),
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

export function setupProfile(
  role: string,
  fullName: string,
): Promise<{ success: boolean; role: string }> {
  return request("/profile/setup", {
    method: "POST",
    body: JSON.stringify({ role, full_name: fullName }),
  });
}
