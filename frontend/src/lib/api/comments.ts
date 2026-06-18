import apiClient from "./client";
import type { CommentResponse, CommentCreate, CommentEdit } from "@/types/api";

export async function listComments(
  entityType: string,
  entityId: string
): Promise<CommentResponse[]> {
  const { data } = await apiClient.get<CommentResponse[]>("/comments/", {
    params: { entity_type: entityType, entity_id: entityId },
  });
  return data;
}

export async function createComment(
  body: CommentCreate
): Promise<CommentResponse> {
  const { data } = await apiClient.post<CommentResponse>("/comments/", body);
  return data;
}

export async function editComment(
  commentId: string,
  body: CommentEdit
): Promise<CommentResponse> {
  const { data } = await apiClient.patch<CommentResponse>(
    `/comments/${commentId}`,
    body
  );
  return data;
}

export async function deleteComment(commentId: string): Promise<void> {
  await apiClient.delete(`/comments/${commentId}`);
}
