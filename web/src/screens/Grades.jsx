import { useEffect, useState } from "react";
import { api } from "../api";

/** Оценки по курсам. Итог за курс выделен — обычно смотрят именно на него. */
export default function Grades() {
  const [rows, setRows] = useState(null);
  const [error, setError] = useState("");

  useEffect(() => {
    api.grades().then(setRows).catch(() => setError("Moodle не отдал оценки"));
  }, []);

  if (error) return <div className="empty">{error}</div>;
  if (!rows) return <p className="loading">Смотрю оценки…</p>;
  if (!rows.length) {
    return (
      <div className="empty">
        Оценок пока нет. В начале семестра это нормально — преподаватели ещё не
        выставили.
      </div>
    );
  }

  const byCourse = rows.reduce((acc, row) => {
    (acc[row.course] ||= []).push(row);
    return acc;
  }, {});

  /* Если по курсу ничего не выставлено, писать «нет оценки» у каждой строки —
     шум. Достаточно сказать это один раз про весь курс. */
  const nothingYet = (items) => items.every((row) => row.grade === "-");

  return (
    <>
      {Object.entries(byCourse).map(([course, items]) => (
        <div className="sect" key={course}>
          <div className="sect-head small">
            <h2>{course}</h2>
            {nothingYet(items) && <span className="when">оценок ещё нет</span>}
          </div>
          <div className="card">
            {items.map((row, i) => (
              <div className={`line${row.is_total ? " total" : ""}`} key={i}>
                <span>{row.item || "Без названия"}</span>
                <span className={`g${row.grade === "-" ? " none" : ""}`}>
                  {row.grade === "-"
                    ? "—"
                    : row.range
                      ? `${row.grade} / ${row.range.split("–")[1]}`
                      : row.grade}
                </span>
              </div>
            ))}
          </div>
        </div>
      ))}
    </>
  );
}
