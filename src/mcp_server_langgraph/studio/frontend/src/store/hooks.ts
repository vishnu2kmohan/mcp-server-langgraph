/**
 * Typed Redux Hooks
 *
 * Use these hooks throughout the app instead of plain useDispatch and useSelector.
 *
 * IMPORTANT: Types are imported from ./types instead of ./index to prevent
 * circular dependencies that cause OOM during test module loading.
 * See: docs-internal/frontend/testing/TESTING_OOM_PREVENTION.md
 */

import { useDispatch, useSelector } from "react-redux";
import type { TypedUseSelectorHook } from "react-redux";
import type { RootState, AppDispatch } from "./types";

// Use throughout your app instead of plain `useDispatch` and `useSelector`
export const useAppDispatch: () => AppDispatch = useDispatch;
export const useAppSelector: TypedUseSelectorHook<RootState> = useSelector;
