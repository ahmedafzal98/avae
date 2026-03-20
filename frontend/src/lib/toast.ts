import { toast as sonnerToast } from "sonner";

/**
 * Task 8.7: Toast notifications for API errors.
 */
export function toastError(message: string) {
  sonnerToast.error(message, { duration: 5000 });
}

export function toastSuccess(message: string) {
  sonnerToast.success(message, { duration: 3000 });
}
