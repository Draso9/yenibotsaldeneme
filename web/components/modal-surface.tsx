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
      dialog.close();
      if (previousFocus?.isConnected && !dialog.contains(previousFocus) && !previousFocus.matches(":disabled")) previousFocus.focus();
      else document.getElementById("main-content")?.focus();
    };
  }, [modal]);

  return <dialog ref={ref} id={id} className={`modal-surface ${className}`}
    aria-label={label} role={modal ? undefined : "region"}
    onCancel={(event) => { event.preventDefault(); onDismiss?.(); }}>
    {children}
  </dialog>;
}
