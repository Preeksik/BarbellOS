import type { NoteBlock, NoteSection } from "../../lib/api";

/** Teksty z pliku planu: akapity, listy z pogrubionym początkiem i tabele (bez HTML-a). */
export function NoteBlocks({ blocks }: { blocks: NoteBlock[] }) {
  return (
    <>
      {blocks.map((block, i) => {
        if (block.type === "list") {
          return (
            <ul key={i} className="notelist">
              {block.items.map((item, j) => (
                <li key={j}>
                  {item.lead && <strong>{item.lead}: </strong>}
                  {item.text}
                </li>
              ))}
            </ul>
          );
        }
        if (block.type === "table") {
          return (
            <div key={i} className="tablewrap">
              <table className="notetable">
                <thead>
                  <tr>
                    {block.head.map((h) => (
                      <th key={h}>{h}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {block.rows.map((row, j) => (
                    <tr key={j}>
                      {row.map((cell, k) => (
                        <td key={k}>{cell}</td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          );
        }
        return <p key={i}>{block.text}</p>;
      })}
    </>
  );
}

export function NoteSections({ sections, as: Heading = "h3" }: { sections: NoteSection[]; as?: "h2" | "h3" }) {
  return (
    <>
      {sections.map((section, i) => (
        <div key={i} className="notesection">
          {section.title && <Heading>{section.title}</Heading>}
          <NoteBlocks blocks={section.blocks} />
        </div>
      ))}
    </>
  );
}
