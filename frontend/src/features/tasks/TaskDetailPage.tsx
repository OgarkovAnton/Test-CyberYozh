import { useEffect, useRef, useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api } from "../../shared/api/client";
import { useAuth } from "../../shared/auth/AuthContext";
import type { Task, UserOption } from "./types";

function errorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string" && detail) {
      return detail;
    }
  }
  return fallback;
}

export function TaskDetailPage() {
  const { taskId = "" } = useParams();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const { user } = useAuth();
  const [body, setBody] = useState("");
  const [assigneeId, setAssigneeId] = useState("");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [editingCommentId, setEditingCommentId] = useState<string | null>(null);
  const [editingBody, setEditingBody] = useState("");
  const [error, setError] = useState<string | null>(null);
  const detailsDirty = useRef(false);
  const savedVersion = useRef(0);

  async function reloadAfterConflict(err: unknown): Promise<void> {
    if (!axios.isAxiosError(err) || err.response?.status !== 409) {
      return;
    }
    detailsDirty.current = false;
    await queryClient.invalidateQueries({ queryKey: ["task", taskId] });
    await queryClient.invalidateQueries({ queryKey: ["tasks"] });
  }

  const taskQuery = useQuery({
    queryKey: ["task", taskId],
    queryFn: async () => {
      const { data } = await api.get<Task>(`/tasks/${taskId}/`);
      return data;
    },
    enabled: Boolean(taskId),
  });

  const { data: users = [] } = useQuery({
    queryKey: ["users"],
    queryFn: async () => {
      const { data } = await api.get<UserOption[]>("/users/");
      return data;
    },
  });

  const invalidate = async () => {
    await queryClient.invalidateQueries({ queryKey: ["task", taskId] });
    await queryClient.invalidateQueries({ queryKey: ["tasks"] });
  };

  const action = useMutation({
    mutationFn: async (path: string) => {
      setError(null);
      await api.post(path);
    },
    onSuccess: async () => {
      detailsDirty.current = false;
      await invalidate();
    },
    onError: async (err: unknown) => {
      setError(errorMessage(err, "Action failed"));
      await reloadAfterConflict(err);
    },
  });

  const assign = useMutation({
    mutationFn: async (nextAssignee: string | null) => {
      setError(null);
      await api.post(`/tasks/${taskId}/assign/`, { assignee_id: nextAssignee });
    },
    onSuccess: async () => {
      detailsDirty.current = false;
      await invalidate();
    },
    onError: async (err: unknown) => {
      setError(errorMessage(err, "Assign failed"));
      await reloadAfterConflict(err);
    },
  });

  const saveDetails = useMutation({
    mutationFn: async () => {
      setError(null);
      await api.put(`/tasks/${taskId}/`, {
        title,
        description,
        version: savedVersion.current,
      });
    },
    onSuccess: async () => {
      detailsDirty.current = false;
      await invalidate();
    },
    onError: async (err: unknown) => {
      setError(errorMessage(err, "Could not save task"));
      await reloadAfterConflict(err);
    },
  });

  const removeTask = useMutation({
    mutationFn: async () => {
      setError(null);
      await api.delete(`/tasks/${taskId}/`);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["tasks"] });
      navigate("/");
    },
    onError: async (err: unknown) => {
      setError(errorMessage(err, "Could not delete task"));
      await reloadAfterConflict(err);
    },
  });

  const addComment = useMutation({
    mutationFn: async () => {
      setError(null);
      await api.post(`/tasks/${taskId}/comments/`, { body });
    },
    onSuccess: async () => {
      setBody("");
      await invalidate();
    },
    onError: async (err: unknown) => {
      setError(errorMessage(err, "Comment failed"));
      await reloadAfterConflict(err);
    },
  });

  const editComment = useMutation({
    mutationFn: async (commentId: string) => {
      setError(null);
      await api.put(`/tasks/${taskId}/comments/${commentId}/`, { body: editingBody });
    },
    onSuccess: async () => {
      setEditingCommentId(null);
      setEditingBody("");
      await invalidate();
    },
    onError: async (err: unknown) => {
      setError(errorMessage(err, "Could not edit comment"));
      await reloadAfterConflict(err);
    },
  });

  const removeComment = useMutation({
    mutationFn: async (commentId: string) => {
      setError(null);
      await api.delete(`/tasks/${taskId}/comments/${commentId}/`);
    },
    onSuccess: invalidate,
    onError: async (err: unknown) => {
      setError(errorMessage(err, "Could not delete comment"));
      await reloadAfterConflict(err);
    },
  });

  function onComment(event: FormEvent) {
    event.preventDefault();
    addComment.mutate();
  }

  function onSaveDetails(event: FormEvent) {
    event.preventDefault();
    saveDetails.mutate();
  }

  useEffect(() => {
    detailsDirty.current = false;
  }, [taskId]);

  useEffect(() => {
    const data = taskQuery.data;
    if (!data || data.id !== taskId || detailsDirty.current) {
      return;
    }
    setTitle(data.title);
    setDescription(data.description);
    setAssigneeId(data.assignee_id ?? "");
    savedVersion.current = data.version;
  }, [taskQuery.data, taskId]);

  if (taskQuery.isLoading) {
    return <p className="muted">Loading task…</p>;
  }

  if (taskQuery.isError || !taskQuery.data) {
    return (
      <div className="stack">
        <Link to="/" className="muted">
          ← Back to list
        </Link>
        <p className="error">{errorMessage(taskQuery.error, "Task could not be loaded")}</p>
      </div>
    );
  }

  const task = taskQuery.data;
  const comments = task.comments ?? [];
  const isPm = Boolean(user?.is_staff);
  const isCreator = user?.id === task.creator_id;
  const canManage = isPm || isCreator;
  const canChangeStatus = canManage || user?.id === task.assignee_id;
  const emails = new Map(users.map((item) => [item.id, item.email]));

  return (
    <div className="stack">
      <Link to="/" className="muted">
        ← Back to list
      </Link>
      <section className="panel stack">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <h1>{task.title}</h1>
          <span className="badge">
            {task.status} · v{task.version}
          </span>
        </div>
        <p>{task.description || "No description"}</p>
        <p className="muted">
          Assignee:{" "}
          {task.assignee_id
            ? emails.get(task.assignee_id) || task.assignee_id
            : "not assigned"}
        </p>
        {error && <p className="error">{error}</p>}
        {canManage && task.status !== "done" && (
          <form className="stack" onSubmit={onSaveDetails}>
            <label>
              Title
              <input
                value={title}
                onChange={(e) => {
                  detailsDirty.current = true;
                  setTitle(e.target.value);
                }}
                required
              />
            </label>
            <label>
              Description
              <textarea
                value={description}
                onChange={(e) => {
                  detailsDirty.current = true;
                  setDescription(e.target.value);
                }}
                rows={3}
              />
            </label>
            <button type="submit" disabled={saveDetails.isPending}>
              Save
            </button>
          </form>
        )}
        <div className="row">
          {canChangeStatus && task.status === "todo" && task.assignee_id && (
            <button
              type="button"
              className="secondary"
              onClick={() => action.mutate(`/tasks/${taskId}/start/`)}
            >
              Start
            </button>
          )}
          {canChangeStatus && task.status === "in_progress" && (
            <button type="button" onClick={() => action.mutate(`/tasks/${taskId}/complete/`)}>
              Complete
            </button>
          )}
          {canChangeStatus && task.status === "in_progress" && (
            <button
              type="button"
              className="secondary"
              onClick={() => action.mutate(`/tasks/${taskId}/return/`)}
            >
              Return to queue
            </button>
          )}
          {canChangeStatus && task.status === "done" && (
            <button
              type="button"
              className="secondary"
              onClick={() => action.mutate(`/tasks/${taskId}/reopen/`)}
            >
              Reopen
            </button>
          )}
          {canManage && task.status === "todo" && (
            <button
              type="button"
              className="danger"
              onClick={() => removeTask.mutate()}
              disabled={removeTask.isPending}
            >
              Delete
            </button>
          )}
        </div>
        {canManage && task.status === "todo" && (
          <div className="row">
            <select
              value={assigneeId}
              onChange={(e) => {
                detailsDirty.current = true;
                setAssigneeId(e.target.value);
              }}
            >
              <option value="">Assign to…</option>
              {users.map((item) => (
                <option key={item.id} value={item.id}>
                  {item.email}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="secondary"
              disabled={!assigneeId || assigneeId === task.assignee_id || assign.isPending}
              onClick={() => assign.mutate(assigneeId)}
            >
              Assign
            </button>
            {task.assignee_id && (
              <button type="button" className="secondary" onClick={() => assign.mutate(null)}>
                Unassign
              </button>
            )}
          </div>
        )}
      </section>

      <section className="panel stack">
        <h2>Comments</h2>
        <form className="stack" onSubmit={onComment}>
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            rows={3}
            required
            placeholder="Write a comment"
          />
          <button type="submit">Add comment</button>
        </form>
        <div className="comments">
          {comments.map((comment) => {
            const mine = comment.author_id === user?.id;
            return (
              <div key={comment.id} className="comment">
                <div className="muted">{emails.get(comment.author_id) || comment.author_id}</div>
                {editingCommentId === comment.id ? (
                  <form
                    className="stack"
                    onSubmit={(event) => {
                      event.preventDefault();
                      editComment.mutate(comment.id);
                    }}
                  >
                    <textarea
                      value={editingBody}
                      onChange={(e) => setEditingBody(e.target.value)}
                      rows={3}
                      required
                    />
                    <div className="row">
                      <button type="submit">Save comment</button>
                      <button
                        type="button"
                        className="secondary"
                        onClick={() => setEditingCommentId(null)}
                      >
                        Cancel
                      </button>
                    </div>
                  </form>
                ) : (
                  <div>{comment.body}</div>
                )}
                {mine && editingCommentId !== comment.id && (
                  <div className="row">
                    <button
                      type="button"
                      className="secondary"
                      onClick={() => {
                        setEditingCommentId(comment.id);
                        setEditingBody(comment.body);
                      }}
                    >
                      Edit
                    </button>
                    <button
                      type="button"
                      className="secondary"
                      onClick={() => removeComment.mutate(comment.id)}
                    >
                      Delete
                    </button>
                  </div>
                )}
              </div>
            );
          })}
          {comments.length === 0 && <p className="muted">No comments yet.</p>}
        </div>
      </section>
    </div>
  );
}
