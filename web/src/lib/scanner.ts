/**
 * Odczyt kodów kreskowych przez zxing-wasm.
 *
 * Safari nie ma wbudowanego Barcode Detection API, stąd WebAssembly. Plik .wasm jest
 * serwowany z naszej domeny (nie z CDN), żeby skaner działał także offline.
 */

import { type ReaderOptions, prepareZXingModule, readBarcodes } from "zxing-wasm/reader";
import wasmUrl from "zxing-wasm/reader/zxing_reader.wasm?url";
import { isValidEan } from "./ean";

prepareZXingModule({
  overrides: {
    locateFile: (path: string, prefix: string) => (path.endsWith(".wasm") ? wasmUrl : prefix + path),
  },
});

const OPTIONS: ReaderOptions = { formats: ["EANUPC"], tryHarder: true, maxNumberOfSymbols: 1 };

async function decode(input: ImageData | Blob): Promise<string | null> {
  const results = await readBarcodes(input, OPTIONS);
  const hit = results.find((r) => r.isValid && isValidEan(r.text));
  return hit ? hit.text : null;
}

/** Odczyt z jednej klatki podglądu kamery. */
export async function decodeVideoFrame(
  video: HTMLVideoElement,
  canvas: HTMLCanvasElement,
): Promise<string | null> {
  if (video.readyState < HTMLMediaElement.HAVE_CURRENT_DATA || video.videoWidth === 0) return null;
  canvas.width = video.videoWidth;
  canvas.height = video.videoHeight;
  const context = canvas.getContext("2d", { willReadFrequently: true });
  if (!context) return null;
  context.drawImage(video, 0, 0);
  return decode(context.getImageData(0, 0, canvas.width, canvas.height));
}

/** Zapas, gdy podgląd na żywo zawodzi: odczyt ze zdjęcia zrobionego aparatem. */
export function decodeImageFile(file: Blob): Promise<string | null> {
  return decode(file);
}
