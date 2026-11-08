import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link, Outlet } from "react-router-dom";
import { api } from "../shared/api/client";
import { useNotificationStream } from "../shared/api/useNotificationStream";
import { useAuth } from "../shared/auth/AuthContext";

type Notice = {
  id: string;
  event_type: string;
  created_at: string;
  read_at: string | null;
};

export function AppLayout() {
  const { user, logout } = useAuth();
  const queryClient = useQueryClient();
  useNotificationStream(Boolean(user));
  const notices = useQuery({
    queryKey: ["notifications"],
    queryFn: async () => {
      const { data } = await api.get<Notice[]>("/notifications/me/");
      return data;
    },
  });
  const markRead = useMutation({
    mutationFn: async (id: string) => {
      await api.post(`/notifications/${id}/read/`);
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["notifications"] });
    },
  });
  const unread = (notices.data ?? []).filter((item) => !item.read_at).length;

  return (
    <div className="shell">
      <header className="topbar">
        <Link to="/" className="brand">
          Task Management
        </Link>
        <div className="row">
          <span className="muted">{user?.email}</span>
          <button type="button" className="secondary" onClick={logout}>
            Log out
          </button>
        </div>
      </header>
      <section className="panel stack" style={{ marginBottom: 16 }}>
        <h2>Notifications{unread > 0 ? ` (${unread})` : ""}</h2>
        {notices.isLoading && <p className="muted">Loading…</p>}
        {(notices.data ?? []).length === 0 && !notices.isLoading && (
          <p className="muted">No notifications.</p>
        )}
        {(notices.data ?? []).map((item) => (
          <div key={item.id} className="row" style={{ justifyContent: "space-between" }}>
            <span>
              {item.event_type}
              {item.read_at ? "" : " · new"}
            </span>
            {!item.read_at && (
              <button type="button" className="secondary" onClick={() => markRead.mutate(item.id)}>
                Mark read
              </button>
            )}
          </div>
        ))}
      </section>
      <Outlet />
    </div>
  );
}
