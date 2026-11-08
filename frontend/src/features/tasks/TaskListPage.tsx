import { useState, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import axios from "axios";
import { Link } from "react-router-dom";
import { api } from "../../shared/api/client";
import type { Task, UserOption } from "./types";

type TaskPage = {
  count: number;
  next: string | null;
  previous: string | null;
  results: Task[];
};

function errorMessage(error: unknown, fallback: string): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail;
    if (typeof detail === "string" && detail) {
      return detail;
    }
  }
  return fallback;
}

export function TaskListPage() {
  const queryClient = useQueryClient();
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [status, setStatus] = useState("");
  const [page, setPage] = useState(1);
  const [error, setError] = useState<string | null>(null);

  const { data: users = [] } = useQuery({
    queryKey: ["users"],
    queryFn: async () => {
      const { data } = await api.get<UserOption[]>("/users/");
      return data;
    },
  });

  const tasksQuery = useQuery({
    queryKey: ["tasks", status, page],
    queryFn: async () => {
      const { data } = await api.get<TaskPage>("/tasks/", {
        params: { page, ...(status ? { status } : {}) },
      });
      return data;
    },
  });

  const createTask = useMutation({
    mutationFn: async () => {
      setError(null);
      await api.post("/tasks/", { title, description });
    },
    onSuccess: async () => {
      setTitle("");
      setDescription("");
      await queryClient.invalidateQueries({ queryKey: ["tasks"] });
    },
    onError: (err: unknown) => setError(errorMessage(err, "Could not create task")),
  });

  function onCreate(event: FormEvent) {
    event.preventDefault();
    createTask.mutate();
  }

  const tasks = tasksQuery.data?.results ?? [];
  const emails = new Map(users.map((item) => [item.id, item.email]));

  return (
    <div className="stack">
      <section className="panel stack">
        <h2>Create task</h2>
        <form className="stack" onSubmit={onCreate}>
          <label>
            Title
            <input value={title} onChange={(e) => setTitle(e.target.value)} required />
          </label>
          <label>
            Description
            <textarea
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              rows={3}
            />
          </label>
          {error && <p className="error">{error}</p>}
          <button type="submit" disabled={createTask.isPending}>
            Create
          </button>
        </form>
      </section>

      <section className="panel stack">
        <div className="row" style={{ justifyContent: "space-between" }}>
          <h2>Tasks</h2>
          <select
            value={status}
            onChange={(e) => {
              setStatus(e.target.value);
              setPage(1);
            }}
          >
            <option value="">All statuses</option>
            <option value="todo">Todo</option>
            <option value="in_progress">In progress</option>
            <option value="done">Done</option>
          </select>
        </div>
        {tasksQuery.isLoading && <p className="muted">Loading…</p>}
        {tasksQuery.isError && (
          <p className="error">{errorMessage(tasksQuery.error, "Could not load tasks")}</p>
        )}
        <div className="task-list">
          {tasks.map((task) => (
            <Link key={task.id} to={`/tasks/${task.id}`} className="task-item">
              <div>
                <strong>{task.title}</strong>
                <div className="muted">{task.description || "No description"}</div>
                <div className="muted">
                  {task.assignee_id
                    ? emails.get(task.assignee_id) || task.assignee_id
                    : "not assigned"}
                </div>
              </div>
              <span className="badge">{task.status}</span>
            </Link>
          ))}
          {!tasksQuery.isLoading && tasks.length === 0 && (
            <p className="muted">No tasks yet. Create the first one.</p>
          )}
        </div>
        <div className="row">
          <button
            type="button"
            className="secondary"
            disabled={!tasksQuery.data?.previous}
            onClick={() => setPage((current) => Math.max(1, current - 1))}
          >
            Previous
          </button>
          <button
            type="button"
            className="secondary"
            disabled={!tasksQuery.data?.next}
            onClick={() => setPage((current) => current + 1)}
          >
            Next
          </button>
        </div>
      </section>
    </div>
  );
}
