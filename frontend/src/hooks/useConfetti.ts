import confetti from "canvas-confetti"

export function fireApplyConfetti() {
  confetti({ particleCount: 50, spread: 60, origin: { y: 0.8 } })
}

export function fireSweepCompleteConfetti() {
  confetti({ particleCount: 30, spread: 40, origin: { y: 0.9 } })
}
