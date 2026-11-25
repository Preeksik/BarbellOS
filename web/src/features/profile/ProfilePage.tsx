import { useMutation, useMutationState, useQuery } from "@tanstack/react-query";
import { type FormEvent, useEffect, useState } from "react";
import {
  type AiUsage,
  type Goal,
  type Lifestyle,
  type Plan,
  type Profile,
  type ProfileResponse,
  type Sex,
  type Targets,
  type TrainingEquipment,
  api,
} from "../../lib/api";
import { toIsoDay } from "../../lib/diary";
import { INVALID, formatDecimal, parseDecimal } from "../../lib/number";
import {
  PROFILE_QUERY_KEY,
  type ProfilePutInput,
  TRAINING_EQUIPMENT_KEY,
  type TargetsPutInput,
  type TrainingEquipmentInput,
  mutationKeys,
} from "../../lib/offline";
import { GOAL_ROWS, KIND_HINT } from "../../lib/targets";
import { THEME_CHOICES, setTheme, useTheme } from "../../lib/theme";
import { formatKcal } from "../diet/macros";
import { HomePage } from "../home/HomePage";

/**
 * Tryb życia BEZ chodzenia i treningów (te liczą się osobno). Procent przemiany
 * spoczynkowej jest kopią z serwera (`core/profile.py`, LIFESTYLES), tylko do opisu.
 */
const LIFESTYLES: { id: Lifestyle; label: string; example: string; share: string }[] = [
  {
    id: "sitting",
    label: "Siedzący",
    example: "nauka, biuro, dojazd autem; większość dnia na krześle",
    share: "+15%",
  },
  {
    id: "mixed",
    label: "Mieszany",
    example: "część dnia na nogach: nauczyciel, laborant, dużo prac w domu",
    share: "+25%",
  },
  {
    id: "standing",
    label: "Praca na stojąco",
    example: "sklep, kuchnia, fryzjer, magazyn bez dźwigania",
    share: "+40%",
  },
  {
    id: "physical",
    label: "Ciężka praca fizyczna",
    example: "budowa, przeprowadzki, rolnictwo",
    share: "+70%",
  },
];

const GOALS: { id: Goal; label: string }[] = [
  { id: "lose", label: "Schudnąć" },
  { id: "maintain", label: "Utrzymać" },
  { id: "gain", label: "Przytyć" },
];

// Kopia listy z serwera (`core/profile.py`, PACES): serwer i tak sprawdza wartość.
const PACES: Record<Goal, number[]> = {
  lose: [0.25, 0.5, 0.75, 1.0],
  maintain: [0],
  gain: [0.1, 0.25, 0.5],
};
const DEFAULT_PACE: Record<Goal, number> = { lose: 0.5, maintain: 0, gain: 0.25 };

/** Profil (waga, wzrost, cel) i wyliczony z niego plan kalorii i makroskładników. */
export function ProfilePage() {
  const profile = useQuery({
    queryKey: PROFILE_QUERY_KEY,
    queryFn: () => api.get<ProfileResponse>("/api/profile"),
  });
  const [editing, setEditing] = useState(false);
  // Zapis profilu czeka w kolejce: plan na ekranie jest jeszcze stary.
  const pending =
    useMutationState({ filters: { mutationKey: mutationKeys.profilePut, status: "pending" } })
      .length > 0;

  return (
    <>
      {profile.error && !profile.data ? (
        <section className="card">
          <p className="error">{profile.error.message}</p>
        </section>
      ) : !profile.data ? (
        <section className="card">
          <p className="muted">Wczytuję profil…</p>
        </section>
      ) : editing || !profile.data.profile ? (
        <ProfileForm
          current={profile.data.profile}
          onDone={profile.data.profile ? () => setEditing(false) : undefined}
          onSaved={() => setEditing(false)}
        />
      ) : (
        <>
          <ProfileSummary profile={profile.data.profile} onEdit={() => setEditing(true)} />
          {pending ? (
            <section className="card">
              <p className="status todo">
                Profil czeka na wysłanie. Plan przeliczy się po powrocie sieci.
              </p>
            </section>
          ) : (
            profile.data.plan && <PlanCard plan={profile.data.plan} />
          )}
        </>
      )}

      <AiUsageCard />

      <EquipmentCard />

      <ThemeCard />

      <details className="card diagnostics">
        <summary>Diagnostyka: serwer, instalacja, próba offline</summary>
        <HomePage />
      </details>
    </>
  );
}

/**
 * Sprzęt na siłowni (25.11.2026): bez talerzy 25 kg talerze na stronę liczą się od 20 kg,
 * a zaciski dokładają 2 × 2,5 kg. Domyślnie są talerze 25 kg i nie ma zacisków.
 */
function EquipmentCard() {
  const equipment = useQuery({
    queryKey: TRAINING_EQUIPMENT_KEY,
    queryFn: () => api.get<TrainingEquipment>("/api/training/equipment"),
  });
  const put = useMutation<void, Error, TrainingEquipmentInput>({
    mutationKey: mutationKeys.trainingEquipment,
  });
  const data = equipment.data;
  if (!data?.has_plan) return null;
  const choose = (patch: Partial<TrainingEquipmentInput>) =>
    put.mutate({ plates_25: data.plates_25, collars: data.collars, ...patch });
  return (
    <section className="card">
      <h2>Trening</h2>
      <fieldset className="segmented">
        <legend>Największy talerz na siłowni</legend>
        {[
          { value: true, label: "25 kg" },
          { value: false, label: "20 kg" },
        ].map(({ value, label }) => (
          <label key={label} className={data.plates_25 === value ? "active" : ""}>
            <input
              type="radio"
              name="plates25"
              checked={data.plates_25 === value}
              onChange={() => choose({ plates_25: value })}
            />
            {label}
          </label>
        ))}
      </fieldset>
      <fieldset className="segmented">
        <legend>Zaciski</legend>
        {[
          { value: false, label: "Bez zacisków" },
          { value: true, label: "2 × 2,5 kg" },
        ].map(({ value, label }) => (
          <label key={label} className={data.collars === value ? "active" : ""}>
            <input
              type="radio"
              name="collars"
              checked={data.collars === value}
              onChange={() => choose({ collars: value })}
            />
            {label}
          </label>
        ))}
      </fieldset>
      <p className="muted">Od tego zależą talerze na stronę przy każdym ćwiczeniu.</p>
    </section>
  );
}

/** Motyw kolorów tego telefonu. Nie trafia na serwer. */
function ThemeCard() {
  const theme = useTheme();
  return (
    <section className="card">
      <h2>Wygląd</h2>
      <fieldset className="segmented">
        <legend className="visually-hidden">Motyw</legend>
        {THEME_CHOICES.map(({ id, label }) => (
          <label key={id} className={theme === id ? "active" : ""}>
            <input
              type="radio"
              name="theme"
              checked={theme === id}
              onChange={() => setTheme(id)}
            />
            {label}
          </label>
        ))}
      </fieldset>
    </section>
  );
}

function ProfileSummary({ profile, onEdit }: { profile: Profile; onEdit: () => void }) {
  const goal = GOALS.find((g) => g.id === profile.goal)?.label;
  const pace = profile.goal === "maintain" ? "" : ` · ${formatDecimal(profile.pace_kg_week)} kg/tydz.`;
  return (
    <section className="card">
      <h2>Profil</h2>
      <p>
        {profile.sex === "male" ? "Mężczyzna" : "Kobieta"} · {formatDecimal(profile.height_cm)} cm ·{" "}
        {formatDecimal(profile.weight_kg)} kg
      </p>
      <p className="muted">
        Tryb życia: {LIFESTYLES.find((l) => l.id === profile.lifestyle)?.label.toLowerCase()} ·{" "}
        {profile.steps_per_day.toLocaleString("pl-PL")} kroków ·{" "}
        {profile.strength_sessions_week > 0
          ? `siłownia ${profile.strength_sessions_week} × ${profile.strength_minutes} min`
          : "bez siłowni"}
        {profile.cardio_minutes_week > 0 && ` · cardio ${profile.cardio_minutes_week} min/tydz.`}
      </p>
      <p className="muted">
        Cel: {goal}
        {pace}
      </p>
      <button type="button" className="link" onClick={onEdit}>
        Zmień profil
      </button>
    </section>
  );
}

function PlanCard({ plan }: { plan: Plan }) {
  const today = toIsoDay(new Date());
  const [applied, setApplied] = useState(false);
  const apply = useMutation<Targets, Error, TargetsPutInput>({ mutationKey: mutationKeys.targetsPut });
  const change =
    plan.adjustment < 0
      ? `deficyt ${formatKcal(-plan.adjustment)} kcal`
      : plan.adjustment > 0
        ? `nadwyżka ${formatKcal(plan.adjustment)} kcal`
        : "bez deficytu";

  return (
    <section className="card plan">
      <h2>Twój plan</h2>
      <p className="kcal">
        <strong>{formatKcal(plan.kcal)}</strong> kcal dziennie
      </p>
      <p className="muted">
        Zapotrzebowanie {formatKcal(plan.tdee)} kcal · {change}
        {plan.pace_kg_week > 0 && ` (≈ ${formatDecimal(plan.pace_kg_week)} kg/tydz.)`}
      </p>
      {plan.warnings.map((warning) => (
        <p key={warning} className="notice">
          {warning}
        </p>
      ))}

      <table className="parts">
        <caption>Na co idą kalorie (dziennie)</caption>
        <tbody>
          {plan.parts.map((part) => (
            <tr key={part.key}>
              <th scope="row">
                {part.label}
                <span className="muted">{part.detail}</span>
              </th>
              <td>{formatKcal(part.kcal)} kcal</td>
            </tr>
          ))}
          <tr className="sum">
            <th scope="row">Zapotrzebowanie</th>
            <td>{formatKcal(plan.tdee)} kcal</td>
          </tr>
        </tbody>
      </table>

      <table>
        <caption>Cele dzienne</caption>
        <tbody>
          {GOAL_ROWS.map(({ key, label, unit, kind }) => {
            const value = plan.goals[key];
            return (
              <tr key={key}>
                <th scope="row">
                  {label} <span className="muted">({KIND_HINT[kind]})</span>
                </th>
                <td>
                  {value == null
                    ? "bez limitu"
                    : `${unit === "kcal" ? formatKcal(value) : formatDecimal(value)} ${unit}`}
                </td>
              </tr>
            );
          })}
        </tbody>
      </table>

      <details>
        <summary>Skąd te liczby</summary>
        <ul className="notes">
          {plan.notes.map((note) => (
            <li key={note}>{note}</li>
          ))}
        </ul>
        <p className="muted">
          To szacunek z ogólnych wzorów, punkt startowy. Po 2–3 tygodniach logowania i ważenia
          plan skorygujemy na podstawie trendu wagi.
        </p>
      </details>

      {applied ? (
        <p className="status ok">Cele dzienne ustawione od dziś. Paski są w dzienniku.</p>
      ) : (
        <button
          type="button"
          className="primary"
          onClick={() => {
            apply.mutate({ dateFrom: today, goals: plan.goals });
            setApplied(true);
          }}
        >
          Ustaw jako cele dzienne od dziś
        </button>
      )}
    </section>
  );
}

interface Texts {
  height: string;
  weight: string;
  protein: string;
  steps: string;
  sessions: string;
  minutes: string;
  cardio: string;
}

/** Liczba całkowita z pola: puste pole = 0, tekst = INVALID. */
function parseCount(text: string): number | typeof INVALID {
  const parsed = parseDecimal(text.replace(/\s/g, ""));
  if (parsed === INVALID) return INVALID;
  return Math.round(parsed ?? 0);
}

function ProfileForm({
  current,
  onDone,
  onSaved,
}: {
  current: Profile | null;
  onDone?: () => void;
  onSaved: () => void;
}) {
  const [sex, setSex] = useState<Sex>(current?.sex ?? "male");
  const [birthDate, setBirthDate] = useState(current?.birth_date ?? "");
  const [lifestyle, setLifestyle] = useState<Lifestyle>(current?.lifestyle ?? "sitting");
  const [goal, setGoal] = useState<Goal>(current?.goal ?? "maintain");
  const [pace, setPace] = useState<number>(current?.pace_kg_week ?? 0);
  const [texts, setTexts] = useState<Texts>({
    height: formatDecimal(current?.height_cm),
    weight: formatDecimal(current?.weight_kg),
    protein: formatDecimal(current?.protein_g_per_kg),
    steps: String(current?.steps_per_day ?? ""),
    sessions: String(current?.strength_sessions_week ?? ""),
    minutes: String(current?.strength_minutes ?? 60),
    cardio: String(current?.cardio_minutes_week ?? ""),
  });
  const [problem, setProblem] = useState<string | null>(null);
  const save = useMutation<ProfileResponse, Error, ProfilePutInput>({
    mutationKey: mutationKeys.profilePut,
  });

  // Bez sieci zapis czeka w kolejce: nie trzymamy użytkownika w formularzu.
  useEffect(() => {
    if (save.isPaused) onSaved();
  }, [save.isPaused, onSaved]);

  function pickGoal(next: Goal) {
    setGoal(next);
    if (!PACES[next].includes(pace)) setPace(DEFAULT_PACE[next]);
  }

  function submit(event: FormEvent) {
    event.preventDefault();
    const height = parseDecimal(texts.height);
    const weight = parseDecimal(texts.weight);
    const protein = parseDecimal(texts.protein);
    if (!birthDate) return setProblem("Podaj datę urodzenia.");
    if (height === INVALID || height == null) return setProblem("Podaj wzrost w centymetrach.");
    if (weight === INVALID || weight == null) return setProblem("Podaj masę ciała w kilogramach.");
    if (protein === INVALID) return setProblem("Białko: wpisz liczbę albo zostaw puste pole.");
    const steps = parseCount(texts.steps);
    const sessions = parseCount(texts.sessions);
    const minutes = parseCount(texts.minutes);
    const cardio = parseCount(texts.cardio);
    if (steps === INVALID) return setProblem("Kroki: wpisz średnią liczbę kroków dziennie.");
    if (sessions === INVALID || minutes === INVALID || cardio === INVALID) {
      return setProblem("Treningi: wpisz liczby albo zostaw puste pola.");
    }
    setProblem(null);
    save.mutate(
      {
        profile: {
          sex,
          birth_date: birthDate,
          height_cm: height,
          weight_kg: weight,
          lifestyle,
          steps_per_day: steps,
          strength_sessions_week: sessions,
          strength_minutes: sessions > 0 ? minutes : 60,
          cardio_minutes_week: cardio,
          goal,
          pace_kg_week: pace,
          protein_g_per_kg: protein,
        },
      },
      { onSuccess: onSaved },
    );
  }

  return (
    <form className="card" onSubmit={submit}>
      <h2>{current ? "Zmień profil" : "Twój profil"}</h2>
      {!current && (
        <p className="muted">
          Na tej podstawie aplikacja oszacuje zapotrzebowanie kaloryczne i zaproponuje cele
          białka, tłuszczu, węglowodanów, błonnika i soli.
        </p>
      )}

      <fieldset className="segmented">
        <legend>Płeć</legend>
        {(
          [
            ["male", "Mężczyzna"],
            ["female", "Kobieta"],
          ] as const
        ).map(([id, label]) => (
          <label key={id} className={sex === id ? "active" : ""}>
            <input type="radio" name="sex" checked={sex === id} onChange={() => setSex(id)} />
            {label}
          </label>
        ))}
      </fieldset>

      <label>
        Data urodzenia
        <input type="date" value={birthDate} onChange={(e) => setBirthDate(e.target.value)} />
      </label>
      <div className="row">
        <label>
          Wzrost (cm)
          <input
            inputMode="decimal"
            value={texts.height}
            onChange={(e) => setTexts({ ...texts, height: e.target.value })}
          />
        </label>
        <label>
          Masa ciała (kg)
          <input
            inputMode="decimal"
            value={texts.weight}
            onChange={(e) => setTexts({ ...texts, weight: e.target.value })}
          />
        </label>
      </div>
      <fieldset className="choices">
        <legend>Tryb życia (bez chodzenia i treningów)</legend>
        {LIFESTYLES.map((l) => (
          <label key={l.id} className={lifestyle === l.id ? "choice active" : "choice"}>
            <input
              type="radio"
              name="lifestyle"
              checked={lifestyle === l.id}
              onChange={() => setLifestyle(l.id)}
            />
            <span>
              <strong>{l.label}</strong> <span className="muted">{l.share}</span>
              <span className="muted">{l.example}</span>
            </span>
          </label>
        ))}
      </fieldset>

      <label>
        Średnio kroków dziennie
        <input
          inputMode="numeric"
          placeholder="np. 5000"
          value={texts.steps}
          onChange={(e) => setTexts({ ...texts, steps: e.target.value })}
        />
        <span className="muted">
          Z aplikacji Zdrowie: Przeglądaj → Aktywność → Kroki → R (rok). Potem przyjdzie stamtąd
          samo.
        </span>
      </label>

      <div className="row">
        <label>
          Treningi siłowe w tygodniu
          <input
            inputMode="numeric"
            placeholder="0"
            value={texts.sessions}
            onChange={(e) => setTexts({ ...texts, sessions: e.target.value })}
          />
        </label>
        <label>
          Minut na trening
          <input
            inputMode="numeric"
            value={texts.minutes}
            onChange={(e) => setTexts({ ...texts, minutes: e.target.value })}
          />
        </label>
      </div>
      <label>
        Cardio, minut w tygodniu (rower, bieganie)
        <input
          inputMode="numeric"
          placeholder="0"
          value={texts.cardio}
          onChange={(e) => setTexts({ ...texts, cardio: e.target.value })}
        />
      </label>

      <fieldset className="segmented">
        <legend>Cel</legend>
        {GOALS.map((g) => (
          <label key={g.id} className={goal === g.id ? "active" : ""}>
            <input type="radio" name="goal" checked={goal === g.id} onChange={() => pickGoal(g.id)} />
            {g.label}
          </label>
        ))}
      </fieldset>
      {goal !== "maintain" && (
        <label>
          Tempo
          <select value={pace} onChange={(e) => setPace(Number(e.target.value))}>
            {PACES[goal].map((p) => (
              <option key={p} value={p}>
                {formatDecimal(p)} kg na tydzień
              </option>
            ))}
          </select>
        </label>
      )}
      <label>
        Białko na kg masy ciała (opcjonalnie)
        <input
          inputMode="decimal"
          placeholder={goal === "lose" ? "domyślnie 2,2" : "domyślnie 1,8"}
          value={texts.protein}
          onChange={(e) => setTexts({ ...texts, protein: e.target.value })}
        />
      </label>

      {(problem || save.error) && <p className="error">{problem ?? save.error?.message}</p>}
      <div className="row">
        {onDone && (
          <button type="button" onClick={onDone}>
            Anuluj
          </button>
        )}
        <button type="submit" className="primary" disabled={save.isPending && !save.isPaused}>
          Zapisz i policz plan
        </button>
      </div>
    </form>
  );
}

const TASK_LABELS: Record<string, string> = {
  label_to_food: "Zdjęcie etykiety",
  meal_photo: "Zdjęcie posiłku",
  text_to_items: "Opis posiłku",
  day_summary: "Podsumowanie dnia",
  week_review: "Przegląd tygodnia",
  food_query: "Tłumaczenie nazw do tabel USDA",
  generic_names: "Polskie nazwy z tabel USDA",
};

/** Licznik kosztów AI w bieżącym miesiącu (etap 2). Koszt według cennika płatnego poziomu. */
function AiUsageCard() {
  const usage = useQuery({
    queryKey: ["ai-usage"],
    queryFn: () => api.get<AiUsage>("/api/ai/usage"),
  });
  if (!usage.data) return null;
  const { runs, cost_usd, by_task, month } = usage.data;
  return (
    <section className="card">
      <h2>AI w tym miesiącu</h2>
      {runs === 0 ? (
        <p className="muted">Jeszcze nie używałeś funkcji AI w {month}.</p>
      ) : (
        <>
          <table>
            <tbody>
              {by_task.map((t) => (
                <tr key={t.task}>
                  <th scope="row">
                    {TASK_LABELS[t.task] ?? t.task}
                    {t.failed > 0 && <span className="muted"> (nieudane: {t.failed})</span>}
                  </th>
                  <td>{t.runs}×</td>
                </tr>
              ))}
            </tbody>
          </table>
          <p className="muted">
            Według cennika płatnego poziomu: {cost_usd.toLocaleString("pl-PL", { maximumFractionDigits: 4 })}{" "}
            USD. Na darmowym kluczu Gemini płacisz 0 zł.
          </p>
        </>
      )}
    </section>
  );
}
