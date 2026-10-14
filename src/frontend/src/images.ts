import { api } from "./api";

type ImageUpload = {
  upload_id: string;
  expires_at: string;
  files: { upload_url: string; method: "PUT"; headers: Record<string, string>; max_size_bytes: number }[];
};

export async function uploadImages<T>(resource: string, files: File[]): Promise<T> {
  const maxSize = (resource.endsWith("/cover") ? 10 : 5) * 1024 * 1024;
  if (!files.length || files.length > 5) throw new Error("Choose between one and five images.");
  for (const file of files) {
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) throw new Error("Choose JPEG, PNG, or WebP images.");
    if (!file.size || file.size > maxSize) throw new Error(`Each image must be between 1 byte and ${maxSize / (1024 * 1024)} MiB.`);
  }
  const upload = await api<ImageUpload>(`${resource}/uploads`, {
    method: "POST",
    body: JSON.stringify({ files: files.map((file) => ({ filename: file.name, content_type: file.type, size_bytes: file.size })) }),
  });
  for (let index = 0; index < files.length; index++) {
    const instructions = upload.files[index];
    let response: Response;
    try {
      response = await fetch(instructions.upload_url, {
        method: instructions.method, headers: instructions.headers, body: files[index], credentials: "omit",
      });
    } catch {
      throw new Error("Could not reach image storage. Please try uploading again.");
    }
    if (!response.ok) throw new Error(response.status === 403 ? "Your image upload expired. Please try again." : "Image upload failed. Please try again.");
  }
  return api<T>(`${resource}/uploads/${upload.upload_id}/complete`, { method: "POST" });
}
