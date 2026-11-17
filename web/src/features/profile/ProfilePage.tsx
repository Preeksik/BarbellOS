import { useMutation, useMutationState, useQuery } from "@tanstack/react-query";
import { type FormEvent, useEffect, useState } from "react";
import {
  type Activity,
  type Goal,
  type Plan,
  type Profile,
  type ProfileResponse,
  type Sex,
  type Targets,
  api,
} from "../../lib/api";
import { toIsoDay } from "../../lib/diary";
import { INVALID, formatDecimal, parseDecimal } from "../../lib/number";
import {
  PROFILE_QUERY_KEY,
  type ProfilePutInput,
  type TargetsPutInput,
  mutationKeys,
} from "../../lib/offline";
import { GOAL_ROWS, KIND_HINT } from "../../lib/targets";
import { formatKcal } from "../diet/macros";
import { HomePage } from "../home/HomePage";

const ACTIVITIES: { id: Activity; label: string }[] = [
  { id: "sedentary", label: "Siedzący tryb, bez treningów" },
  { id: "light", label: "1–3 treningi w tygodniu" },
  { id: "moderate", label: "3–5 treningów w tygodniu" },
  { id: "active", label: "6–7 treningów w tygodniu" },
  { id: "very_active", label: "Praca fizyczna i codzienne treningi" },
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

      <details className="card diagnostics">
        <summary>Diagnostyka: serwer, instalacja, próba offline</summary>
        <HomePage />
      </details>
    </>
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
        {ACTIVITIES.find((a) => a.id === profile.activity)?.label} · Cel: {goal}
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

      <table>
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
  const [activity, setActivity] = useState<Activity>(current?.activity ?? "moderate");
  const [goal, setGoal] = useState<Goal>(current?.goal ?? "maintain");
  const [pace, setPace] = useState<number>(current?.pace_kg_week ?? 0);
  const [texts, setTexts] = useState<Texts>({
    height: formatDecimal(current?.height_cm),
    weight: formatDecimal(current?.weight_kg),
    protein: formatDecimal(current?.protein_g_per_kg),
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
    setProblem(null);
    save.mutate(
      {
        profile: {
          sex,
          birth_date: birthDate,
          height_cm: height,
          weight_kg: weight,
          activity,
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
      <label>
        Aktywność
        <select value={activity} onChange={(e) => setActivity(e.target.value as Activity)}>
          {ACTIVITIES.map((a) => (
            <option key={a.id} value={a.id}>
              {a.label}
            </option>
          ))}
        </select>
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
