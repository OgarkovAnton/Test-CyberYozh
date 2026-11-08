export type Comment = {
  id: string;
  author_id: string;
  body: string;
  created_at: string;
  updated_at: string;
};

export type Task = {
  id: string;
  title: string;
  description: string;
  status: "todo" | "in_progress" | "done";
  creator_id: string;
  assignee_id: string | null;
  created_at: string;
  updated_at: string;
  completed_at: string | null;
  version: number;
  comments?: Comment[];
};

export type UserOption = {
  id: string;
  email: string;
};
