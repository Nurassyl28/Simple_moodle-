import { X } from "lucide-react";

/**
 * Профиль: выход и удаление аккаунта.
 *
 * Раньше обе ссылки висели красными прямо под содержимым каждой вкладки —
 * «Выйти» читалось как ошибка, а «Удалить аккаунт» стояло в одном клике от
 * случайного нажатия. Теперь они здесь, и опасное отличается от обычного.
 */
export default function ProfileSheet({ fullname, onClose, onLogout, onDelete }) {
  return (
    <div className="scrim" onClick={onClose}>
      <div className="sheet" onClick={(e) => e.stopPropagation()}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3>{fullname}</h3>
          <button className="tool" onClick={onClose} aria-label="Закрыть"><X size={16} /></button>
        </div>
        <p className="hint">
          Вход в Moodle идёт по токену, пароль нигде не сохранён. При выходе токен
          удаляется с сервера.
        </p>
        <div className="sheet-actions">
          <button onClick={onLogout}>Выйти</button>
          <button className="danger-btn" onClick={onDelete}>
            Удалить аккаунт и все данные
          </button>
        </div>
      </div>
    </div>
  );
}
