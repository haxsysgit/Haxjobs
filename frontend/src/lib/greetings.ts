const starters = [
  "Yo",
  "Hey",
  "There you are",
  "Been waiting for you",
  "What's good",
  "Alright",
  "Aye",
  "Oi",
  "How far",
  "Sup",
]

export function pickGreeting(): string {
  return starters[Math.floor(Math.random() * starters.length)]
}

export function firstName(fullName: string): string {
  return fullName.split(" ")[0] || fullName
}
