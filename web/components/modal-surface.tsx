"use client";

import { type ReactNode, useLayoutEffect, useRef } from "react";

type ModalSurfaceProps = {
  children: ReactNode;
  className: string;
  label: string;
  id?: string;
  modal?: boolean;
  onDismiss?: () => void;
};

function canReturnFocus(element: HTMLElement | null, dialog: HTMLDialogElement) {
  return Boolean(
    element
    && element !== document.body
    && element !== document.documentElement
    && element.isConnected
    && !dialog.contains(element)
    && !element.matches(":disabled")
    && element.getClientRects().length > 0
  );
}

// The same DOM subtree stays mounted when an inline result expands.
export function ModalSurface({ children, className, label, id, modal = true, onDismiss }: ModalSurfaceProps) {
  const ref = useRef<HTMLDialogElement>(null);
  const returnFocus = useRef<HTMLElement | null>(null);
  useLayoutEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (!modal) {
      dialog.open = true;
      returnFocus.current?.focus();
      returnFocus.current = null;
      return;
    }
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    returnFocus.current = previousFocus;
    if (dialog.open) dialog.close();
    dialog.showModal();
    dialog.querySelector<HTMLElement>("[data-modal-focus]")?.focus();
    return () => {
      const fallback = document.getElementById("main-content");
      const target = canReturnFocus(previousFocus, dialog) ? previousFocus : fallback;
      dialog.close();
      requestAnimationFrame(() => {
        if (target?.isConnected) target.focus();
        else document.getElementById("main-content")?.focus();
      });
    };
  }, [modal]);

  return <dialog ref={ref} id={id} className={`modal-surface ${className}`}
    aria-label={label} role={modal ? undefined : "region"}
    onCancel={(event) => { event.preventDefault(); onDismiss?.(); }}>
    {children}
  </dialog>;
}
