export const INDIA_STATES = [
  "Andaman and Nicobar Islands",
  "Andhra Pradesh",
  "Arunachal Pradesh",
  "Assam",
  "Bihar",
  "Chandigarh",
  "Chhattisgarh",
  "Dadra and Nagar Haveli and Daman and Diu",
  "Delhi",
  "Goa",
  "Gujarat",
  "Haryana",
  "Himachal Pradesh",
  "Jammu and Kashmir",
  "Jharkhand",
  "Karnataka",
  "Kerala",
  "Ladakh",
  "Lakshadweep",
  "Madhya Pradesh",
  "Maharashtra",
  "Manipur",
  "Meghalaya",
  "Mizoram",
  "Nagaland",
  "Odisha",
  "Puducherry",
  "Punjab",
  "Rajasthan",
  "Sikkim",
  "Tamil Nadu",
  "Telangana",
  "Tripura",
  "Uttar Pradesh",
  "Uttarakhand",
  "West Bengal",
] as const

const byKey = new Map(INDIA_STATES.map((name) => [name.toUpperCase(), name]))
const aliases: Record<string, string> = {
  "ANDAMAN AND NICOBAR": "ANDAMAN AND NICOBAR ISLANDS",
  "DADRA AND NAGAR HAVELI": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
  "DAMAN AND DIU": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
  "THE DADRA AND NAGAR HAVELI AND DAMAN AND DIU": "DADRA AND NAGAR HAVELI AND DAMAN AND DIU",
  "NCT OF DELHI": "DELHI",
  "NCT DELHI": "DELHI",
  MAHARASTRA: "MAHARASHTRA",
  ORISSA: "ODISHA",
  PONDICHERRY: "PUDUCHERRY",
  "U T OF PUDUCHERRY": "PUDUCHERRY",
  TAMILNADU: "TAMIL NADU",
  UTTARANCHAL: "UTTARAKHAND",
  UTTRANCHAL: "UTTARAKHAND",
}

export function canonicalStateName(value: string): string | null {
  const key = value
    .toUpperCase()
    .replace(/&/g, " AND ")
    .replace(/[^A-Z0-9 ]/g, " ")
    .replace(/\s+/g, " ")
    .trim()
  return byKey.get(aliases[key] ?? key) ?? null
}
