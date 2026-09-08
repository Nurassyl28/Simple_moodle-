/* Форматирование дат. Перенесено из legacy/homework-tracker.jsx. */

export const DAYS_RU = [
  "Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье",
];
export const SHORT_RU = ["пн", "вт", "ср", "чт", "пт", "сб", "вс"];
export const MONTHS_RU = [
  "янв", "фев", "мар", "апр", "мая", "июн", "июл", "авг", "сен", "окт", "ноя", "дек",
];
const PALETTE = ["#2F5DE0", "#D14A32", "#17806A", "#7C4DD1", "#B87400", "#0F6E8C", "#B0286B", "#4F7A17"];
export const TODO_COLOR = "#8A94A6";

export const iso = (d) => {
  const p = (n) => String(n).padStart(2, "0");
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
};

export const fromIso = (s) => {
  const [y, m, d] = s.split("-").map(Number);
  return new Date(y, m - 1, d);
};

export const addDays = (d, n) => {
  const c = new Date(d);
  c.setDate(c.getDate() + n);
  return c;
};

/* Понедельник — нулевой день, как в расписании СДУ. */
export const dayIndex = (d) => (d.getDay() + 6) % 7;

export const pretty = (s) => {
  const d = fromIso(s);
  return `${SHORT_RU[dayIndex(d)]}, ${d.getDate()} ${MONTHS_RU[d.getMonth()]}`;
};

export const daysBetween = (fromI, toI) =>
  Math.round((fromIso(toI) - fromIso(fromI)) / 86400000);

export const inWord = (n) => {
  if (n === 0) return "сегодня";
  if (n === 1) return "завтра";
  if (n === 2) return "послезавтра";
  const last = n % 10, two = n % 100;
  const w = two > 10 && two < 20 ? "дней" : last === 1 ? "день" : last >= 2 && last <= 4 ? "дня" : "дней";
  return `через ${n} ${w}`;
};

export const agoWord = (n) => {
  if (n === 1) return "вчера";
  const last = n % 10, two = n % 100;
  const w = two > 10 && two < 20 ? "дней" : last === 1 ? "день" : last >= 2 && last <= 4 ? "дня" : "дней";
  return `${n} ${w} назад`;
};

/* Один и тот же предмет всегда одного цвета — узнаётся без чтения. */
export const colorFor = (name) => {
  if (!name) return TODO_COLOR;
  let h = 0;
  for (let i = 0; i < name.length; i++) h = (h * 31 + name.charCodeAt(i)) >>> 0;
  return PALETTE[h % PALETTE.length];
};

/* Unix-время из Moodle → человеческая строка. */
export const prettyStamp = (unix) => {
  const d = new Date(unix * 1000);
  const time = `${String(d.getHours()).padStart(2, "0")}:${String(d.getMinutes()).padStart(2, "0")}`;
  return `${SHORT_RU[dayIndex(d)]}, ${d.getDate()} ${MONTHS_RU[d.getMonth()]}, ${time}`;
};
