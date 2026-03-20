"use client";

import { Suspense, useState, useMemo } from "react";
import { useSearchParams } from "next/navigation";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { FileDropzone } from "@/components/upload/FileDropzone";
import { AuditTargetSelect } from "@/components/upload/AuditTargetSelect";
import { LiveEngineStatus } from "@/components/upload/LiveEngineStatus";
import { InstancePerformance } from "@/components/upload/InstancePerformance";
import { useUpload } from "@/hooks/useUpload";
import type { AuditTarget } from "@/types/audit-target";
import { toastError } from "@/lib/toast";
import { Loader2 } from "lucide-react";

function UploadPageContent() {
  const searchParams = useSearchParams();
  const remediationCheckpointId = useMemo(
    () => searchParams.get("remediation_for_checkpoint_id"),
    [searchParams]
  );
  const isRemediationMode = Boolean(remediationCheckpointId);

  const [selectedFiles, setSelectedFiles] = useState<File[]>([]);
  const [auditTarget, setAuditTarget] = useState<AuditTarget>("companies_house");
  const [taskIds, setTaskIds] = useState<string[]>([]);

  const upload = useUpload();

  const handleUpload = () => {
    if (selectedFiles.length === 0) return;
    upload.mutate(
      {
        files: selectedFiles,
        auditTarget,
        remediationForCheckpointId: isRemediationMode
          ? remediationCheckpointId
          : null,
      },
      {
        onSuccess: (data) => {
          setTaskIds(data.task_ids);
          setSelectedFiles([]);
        },
        onError: (err) => {
          toastError(err instanceof Error ? err.message : "Upload failed");
        },
      }
    );
  };

  return (
    <div className="flex flex-col gap-6 p-6">
      {/* Page header */}
      <div>
        <h1 className="text-heading-lg tracking-tight text-foreground">
          {isRemediationMode
            ? "Upload Replacement Document"
            : "Ingestion Terminal"}
        </h1>
        <p className="mt-1 text-body text-muted-foreground">
          {isRemediationMode
            ? "Attach replacement file for AWAITING_CLIENT_REMEDIATION checkpoint"
            : "Upload regulatory documentation for automated extraction and cross-reference verification against statutory databases."}
        </p>
      </div>

      <div className="grid gap-6 lg:grid-cols-[1fr_320px]">
        {/* Left: Upload zone + config */}
        <div className="flex flex-col gap-6">
          {/* Upload zone */}
          <div className="rounded-lg border border-[#e2e8f0] bg-white p-6">
            <FileDropzone
              selectedFiles={selectedFiles}
              onFilesSelected={setSelectedFiles}
              onClear={() => setSelectedFiles([])}
              singleFile={isRemediationMode}
              singleFileLabel="Drop Replacement Document"
            />
            {selectedFiles.length > 0 && (
              <div className="mt-4 flex justify-end">
                <Button
                  onClick={handleUpload}
                  disabled={upload.isPending}
                  className="bg-[#020617] text-white hover:bg-[#0f172a]"
                >
                  {upload.isPending ? (
                    <>
                      <Loader2 className="size-4 animate-spin" />
                      Uploading…
                    </>
                  ) : (
                    "Upload"
                  )}
                </Button>
              </div>
            )}
          </div>

          {/* Configuration — Audit Target */}
          {!isRemediationMode && (
            <Card className="border-[#e2e8f0] max-w-sm">
              <CardContent className="pt-4">
                <label className="mb-2 block text-label uppercase tracking-wider text-[#64748b]">
                  Audit Target
                </label>
                <AuditTargetSelect
                  value={auditTarget}
                  onValueChange={setAuditTarget}
                  className="h-10 w-full rounded-lg border border-[#e2e8f0] bg-white px-3 text-body"
                />
              </CardContent>
            </Card>
          )}
        </div>

        {/* Right: Live Engine Status + Instance Performance */}
        <div className="flex flex-col gap-4">
          <LiveEngineStatus taskIds={taskIds} />
          <InstancePerformance />
        </div>
      </div>

      {upload.isError && (
        <p className="text-sm text-destructive">
          {upload.error instanceof Error
            ? upload.error.message
            : "Upload failed"}
        </p>
      )}
    </div>
  );
}

export default function UploadPage() {
  return (
    <Suspense fallback={<div className="p-6">Loading…</div>}>
      <UploadPageContent />
    </Suspense>
  );
}
