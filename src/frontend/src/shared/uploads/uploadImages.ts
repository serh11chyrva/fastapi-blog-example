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

type ImagePurpose = "avatars" | "profile-banners" | "post-images" | "article-covers" | "article-images";

function imagePurpose(resource: string): ImagePurpose {
  if (resource === "/me/avatar") return "avatars";
  if (resource === "/me/banner") return "profile-banners";
  if (/^\/posts\/[^/]+\/images$/.test(resource)) return "post-images";
  if (/^\/articles\/[^/]+\/cover$/.test(resource)) return "article-covers";
  if (/^\/articles\/[^/]+\/images$/.test(resource)) return "article-images";
  throw new Error("Unsupported image upload destination.");
}

export function validateImages(purpose: ImagePurpose, files: File[]) {
  const post = purpose === "post-images";
  const allowsGif = post || purpose === "article-images";
  if (!files.length || files.length > (post ? 5 : 1))
    throw new Error(post ? "Choose between one and five images, or one GIF." : "Choose exactly one file.");
  if (post && files.length > 1 && files.some((file) => file.type === "image/gif"))
    throw new Error("Choose one GIF without other images for a post or comment.");
  for (const file of files) {
    const gif = file.type === "image/gif";
    if (gif && !allowsGif)
      throw new Error("GIF images are only supported in posts, comments, and article bodies.");
    if (!gif && !["image/jpeg", "image/png", "image/webp"].includes(file.type))
      throw new Error(allowsGif ? "Choose JPEG, PNG, WebP, or GIF files." : "Choose JPEG, PNG, or WebP images.");
    const maxSize = (gif ? 8 : purpose === "article-covers" ? 10 : 5) * 1024 * 1024;
    if (!file.size || file.size > maxSize)
      throw new Error(`Each ${gif ? "GIF" : "image"} must be between 1 byte and ${maxSize / (1024 * 1024)} MiB.`);
  }
}

type PendingUpload = { files: File[]; instructions: ImageUpload; uploaded: boolean };

export function useImageUploader() {
  const pending = useRef(new Map<string, PendingUpload>());
  return async function uploadImages<T>(resource: string, files: File[]): Promise<T> {
    validateImages(imagePurpose(resource), files);
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
