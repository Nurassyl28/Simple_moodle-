/**
 * Единственное место, где фронт говорит с бэкендом.
 *
 * Всё идёт через gateway на /api. Сессия живёт в httpOnly-cookie, поэтому
 * credentials: "include" обязателен, а самого идентификатора сессии в коде нет —
 * скрипт до него не дотягивается, и это сделано намеренно.
 */

class ApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

async function request(path, { method = "GET", body } = {}) {
  const response = await fetch(`/api${path}`, {
    method,
    credentials: "include",
    headers: body ? { "Content-Type": "application/json" } : undefined,
    body: body ? JSON.stringify(body) : undefined,
  });

  if (response.status === 204) return null;

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    throw new ApiError(response.status, payload?.detail || "Что-то пошло не так");
  }
  return payload;
}

/** Загрузка файла: Content-Type ставит браузер сам, вместе с границей формы. */
async function upload(path, file) {
  const form = new FormData();
  form.append("file", file);

  const response = await fetch(`/api${path}`, {
    method: "POST",
    credentials: "include",
    body: form,
  });

  let payload = null;
  try {
    payload = await response.json();
  } catch {
    payload = null;
  }

  if (!response.ok) {
    throw new ApiError(response.status, payload?.detail || "Не получилось прочитать файл");
  }
  return payload;
}

export const api = {
  login: (username, password) => request("/login", { method: "POST", body: { username, password } }),
  logout: () => request("/logout", { method: "POST" }),
  deleteAccount: () => request("/account", { method: "DELETE" }),

  me: () => request("/me"),
  grades: () => request("/grades"),
  files: () => request("/files"),
  deadlines: () => request("/deadlines"),
  importDeadlines: () => request("/deadlines/import", { method: "POST" }),

  tasks: () => request("/tasks"),
  grouped: () => request("/tasks/grouped"),
  createTask: (task) => request("/tasks", { method: "POST", body: task }),
  patchTask: (id, changes) => request(`/tasks/${id}`, { method: "PATCH", body: changes }),
  deleteTask: (id) => request(`/tasks/${id}`, { method: "DELETE" }),
  importTasks: (raw) => request("/tasks/import", { method: "POST", body: { raw } }),

  timetable: () => request("/timetable"),
  parseScheduleHtml: (html) => request("/timetable/parse-html", { method: "POST", body: { html } }),
  parseScheduleImage: (file) => upload("/timetable/parse-image", file),
  saveTimetable: (classes, replace) =>
    request("/timetable/bulk", { method: "POST", body: { classes, replace } }),
  addClass: (item) => request("/timetable", { method: "POST", body: item }),
  deleteClass: (id) => request(`/timetable/${id}`, { method: "DELETE" }),
};

export { ApiError };
