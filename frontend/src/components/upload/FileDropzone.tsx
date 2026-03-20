"use client";

import { useCallback, useRef, useState } from "react";
import { FilePlus, X } from "lucide-react";
import { cn } from "@/lib/utils";

const ACCEPTED_TYPES = [".pdf", ".docx"];
const MAX_SIZE_BYTES = 250 * 1024 * 1024; // 250MB

export interface FileDropzoneProps {
  onFilesSelected: (files: File[]) => void;
  selectedFiles?: File[];
  onClear?: () => void;
  disabled?: boolean;
  className?: string;
  /** When true, single-file mode only (e.g. remediation upload) */
  singleFile?: boolean;
  /** Custom label when in single-file mode */
  singleFileLabel?: string;
}

function validateFile(file: File): string | null {
  const ext = "." + file.name.split(".").pop()?.toLowerCase();
  if (!ACCEPTED_TYPES.includes(ext)) {
    return `Invalid type: ${file.name}. Use PDF or DOCX.`;
  }
  if (file.size > MAX_SIZE_BYTES) {
    return `${file.name} exceeds 250MB limit.`;
  }
  return null;
}

export function FileDropzone({
  onFilesSelected,
  selectedFiles = [],
  onClear,
  disabled = false,
  className,
  singleFile = false,
  singleFileLabel = "Drop Replacement Document",
}: FileDropzoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const processFiles = useCallback(
    (fileList: FileList | null) => {
      if (!fileList?.length) return;
      setError(null);
      const valid: File[] = [];
      const errors: string[] = [];
      const limit = singleFile ? 1 : fileList.length;
      for (let i = 0; i < fileList.length && valid.length < limit; i++) {
        const file = fileList[i];
        const err = validateFile(file);
        if (err) errors.push(err);
        else valid.push(file);
      }
      if (errors.length) setError(errors[0]);
      if (valid.length) onFilesSelected(valid);
    },
    [onFilesSelected, singleFile]
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      if (disabled) return;
      processFiles(e.dataTransfer.files);
    },
    [disabled, processFiles]
  );

  const handleDragOver = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (!disabled) setIsDragging(true);
    },
    [disabled]
  );

  const handleDragLeave = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      if (!e.currentTarget.contains(e.relatedTarget as Node)) setIsDragging(false);
    },
    []
  );

  const handleChange = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      processFiles(e.target.files);
      e.target.value = "";
    },
    [processFiles]
  );

  const inputRef = useRef<HTMLInputElement>(null);
  const hasFiles = selectedFiles.length > 0;

  const triggerSelect = useCallback(() => {
    inputRef.current?.click();
  }, []);

  return (
    <div className={cn("space-y-3", className)}>
      <div
        onDrop={handleDrop}
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        className={cn(
          "flex min-h-[280px] cursor-pointer flex-col items-center justify-center gap-5 rounded-lg border-2 border-dashed transition-colors",
          isDragging && !disabled && "border-primary bg-primary/5",
          !isDragging && "border-[#e2e8f0] bg-[#f8fafc] hover:border-[#cbd5e1] hover:bg-[#f1f5f9]",
          disabled && "cursor-not-allowed opacity-60",
          error && "border-destructive/50"
        )}
        onClick={() => !hasFiles && inputRef.current?.click()}
      >
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED_TYPES.join(",")}
          multiple={!singleFile}
          onChange={handleChange}
          disabled={disabled}
          className="sr-only"
        />
        {hasFiles ? (
          <div className="flex flex-col items-center gap-2 px-4">
            <div className="rounded-full bg-tertiary/20 p-3">
              <FilePlus className="size-8 text-tertiary" />
            </div>
            <p className="text-body font-medium text-foreground">
              {selectedFiles.length} file{selectedFiles.length !== 1 ? "s" : ""}{" "}
              selected
            </p>
            <p className="text-body text-muted-foreground">
              {selectedFiles.map((f) => f.name).join(", ")}
            </p>
            {onClear && (
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault();
                  e.stopPropagation();
                  onClear();
                }}
                className="mt-2 flex items-center gap-1.5 rounded-md px-3 py-1.5 text-body text-muted-foreground hover:bg-muted hover:text-foreground"
              >
                <X className="size-4" />
                Clear
              </button>
            )}
          </div>
        ) : (
          <>
            <div className="rounded-full bg-muted/80 p-5">
              <FilePlus className="size-12 text-muted-foreground" />
            </div>
            <div className="text-center space-y-1">
              <p className="text-body font-medium text-foreground">
                {singleFile ? singleFileLabel : "Drop Verification Payload"}
              </p>
              <p className="text-body text-muted-foreground">
                Accepting PDF, DOCX (Max 250MB)
              </p>
            </div>
            <button
              type="button"
              onClick={(e) => {
                e.preventDefault();
                e.stopPropagation();
                triggerSelect();
              }}
              className="mt-1 inline-flex items-center justify-center rounded-lg bg-[#020617] px-4 py-2 text-body font-medium text-white hover:bg-[#0f172a] transition-colors"
            >
              Select from System
            </button>
          </>
        )}
      </div>
      {error && (
        <p className="text-body text-destructive" role="alert">
          {error}
        </p>
      )}
    </div>
  );
}
