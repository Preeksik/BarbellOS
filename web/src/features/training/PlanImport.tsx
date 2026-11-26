import { useMutation, useQueryClient } from "@tanstack/react-query";
import { type ChangeEvent, useState } from "react";
import { type TrainingImportResult, api } from "../../lib/api";

/**
 * Wgranie planu z pliku JSON: sam plan albo plan z dziennikiem ze starego pliku HTML
 * (`{ plan, settings, logs }`). Wymaga sieci; sesje z pliku zastępują te same w bazie.
 */
export function PlanImport({
  first = false,
  inline = false,
}: {
  first?: boolean;
  /** W Profilu: bez własnej karty i od razu otwarte. */
  inline?: boolean;
}) {
  const queryClient = useQueryClient();
  const [open, setOpen] = useState(first || inline);
  const upload = useMutation<TrainingImportResult, Error, File>({
    mutationFn: async (file) => {
      let parsed: unknown;
      try {
        parsed = JSON.parse(await file.text());
      } catch {
        throw new Error("To nie jest plik JSON z planem.");
      }
      const body =
        parsed && typeof parsed === "object" && "plan" in parsed ? parsed : { plan: parsed };
      return api.put<TrainingImportResult>("/api/training/plan", body);
    },
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["training"] }),
  });

  function pick(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (file) upload.mutate(file);
  }

  if (!open) {
    return (
      <button type="button" className="link" onClick={() => setOpen(true)}>
        Wczytaj plan z pliku
      </button>
    );
  }
  const Wrapper = inline ? "div" : "section";
  return (
    <Wrapper className={inline ? "planimport" : "card"}>
      {!inline && <h2>{first ? "Wgraj plan treningowy" : "Wczytaj plan z pliku"}</h2>}
      <p className="muted">
        Plik JSON z planem albo z planem i dziennikiem ze starego pliku. Sesje z pliku zastąpią
        te same sesje w aplikacji, pozostałe zostaną.
      </p>
      <label className={upload.isPending ? "file busy" : "file"}>
        {upload.isPending ? "Wgrywam…" : "Wybierz plik"}
        <input type="file" accept="application/json,.json" onChange={pick} />
      </label>
      {upload.error && <p className="error">{upload.error.message}</p>}
      {upload.data && (
        <p className="status ok">
          Wgrano „{upload.data.plan_name}": {upload.data.weeks} tygodni, {upload.data.sessions} sesji,
          z dziennika {upload.data.imported_sessions}.
          {upload.data.skipped.length > 0 && ` Pominięte: ${upload.data.skipped.join(", ")}.`}
        </p>
      )}
    </Wrapper>
  );
}
