/** Fired (on window) to open the sign-in dialog from anywhere in the console. */
export const OPEN_SIGNIN_EVENT = 'ff-signin-open'

export function openSignIn(): void {
  window.dispatchEvent(new Event(OPEN_SIGNIN_EVENT))
}
