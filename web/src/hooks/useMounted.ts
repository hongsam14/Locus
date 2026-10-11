// Whether the component is still on screen (V4 code review 01 #9): a navigate or a write
// that answers after the screen was left must not run — react-router's navigate still
// pushes after unmount. Set in the effect body, so StrictMode's second mount sets it again.
import { useEffect, useRef, type MutableRefObject } from "react";

export function useMounted(): MutableRefObject<boolean> {
  const mounted = useRef(true);
  useEffect(() => {
    mounted.current = true;
    return () => {
      mounted.current = false;
    };
  }, []);
  return mounted;
}
