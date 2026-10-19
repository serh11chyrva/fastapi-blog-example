import { useRef } from "react";
import { api, ApiError } from "../api/client";

type ImageUpload = {
  upload_id: string;
  expires_at: string;
  files: {
    upload_url: string;
    method: "PUT";
    headers: Record<string, string>;
    max_size_bytes: number;
  }[];
};

export function validateImages(resource: string, files: File[]) {
  const maxSize = (resource.endsWith("/cover") ? 10 : 5) * 1024 * 1024;
  if (!files.length || files.length > 5)
    throw new Error("Choose between one and five images.");
  for (const file of files) {
    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type))
      throw new Error("Choose JPEG, PNG, or WebP images.");
    if (!file.size || file.size > maxSize)
      throw new Error(`Each image must be between 1 byte and ${maxSize / (1024 * 1024)} MiB.`);
  }
}

type PendingUpload = { files: File[]; instructions: ImageUpload; uploaded: boolean };

export function useImageUploader() {
  const pending = useRef(new Map<string, PendingUpload>());
  return async function uploadImages<T>(resource: string, files: File[]): Promise<T> {
    validateImages(resource, files);
    let task = pending.current.get(resource);
    if (!task || task.files.length !== files.length || task.files.some((file, index) => file !== files[index])) {
      const instructions = await api<ImageUpload>(`${resource}/uploads`, {
        method: "POST",
        body: JSON.stringify({ files: files.map((file) => ({ filename: file.name, content_type: file.type, size_bytes: file.size })) }),
      });
      task = { files: [...files], instructions, uploaded: false };
      pending.current.set(resource, task);
    }
    if (!task.uploaded) {
      if (Date.parse(task.instructions.expires_at) <= Date.now()) {
        pending.current.delete(resource);
        throw new Error("Your image upload expired. Please try uploading again.");
      }
      for (let index = 0; index < files.length; index++) {
        const instructions = task.instructions.files[index];
        if (!instructions) throw new Error("The server returned incomplete upload instructions.");
        let response: Response;
        try {
          response = await fetch(instructions.upload_url, {
            method: instructions.method, headers: instructions.headers, body: files[index], credentials: "omit",
          });
        }
        catch {
          throw new Error("Could not reach image storage. Please try uploading again.");
        }
        if (!response.ok)
          throw new Error(response.status === 403 ? "Your image upload expired. Please try again." : "Image upload failed. Please try again.");
      }
      task.uploaded = true;
    }
    try {
      const result = await api<T>(`${resource}/uploads/${task.instructions.upload_id}/complete`, { method: "POST" });
      pending.current.delete(resource);
      return result;
    } catch (reason) {
      if (reason instanceof ApiError && (reason.status === 404
          || (reason.status === 409 && reason.message === "Upload has expired; request new upload URLs"))) {
        pending.current.delete(resource);
      }
      throw reason;
    }
  };
}
