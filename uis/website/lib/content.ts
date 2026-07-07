export type ServiceInfo = {
  title: string;
  description: string;
};

export type Metric = {
  label: string;
  value: string;
  note: string;
};

export type LocationInfo = {
  region: string;
  clinics: number;
  highlights: string;
};

export const services: ServiceInfo[] = [
  {
    title: "Primary and Preventive Care",
    description:
      "Same-day access, extended clinic hours, and long-term preventive programmes to reduce avoidable admissions.",
  },
  {
    title: "Specialist and Chronic Care",
    description:
      "Coordinated care pathways for ongoing conditions with multidisciplinary clinical teams across US and UK clinics.",
  },
  {
    title: "Patient Journey Support",
    description:
      "Appointment management, reminders, and post-visit follow-up focused on reducing no-show events and improving outcomes.",
  },
];

export const metrics: Metric[] = [
  {
    label: "Clinics in operation",
    value: "12",
    note: "9 in the US and 3 in the UK",
  },
  {
    label: "Team members",
    value: "200+",
    note: "Clinical, operational, and technology teams",
  },
  {
    label: "Annual revenue",
    value: "$28M",
    note: "Across outpatient operations",
  },
  {
    label: "Current no-show rate",
    value: "22%",
    note: "Network-wide patient access challenge",
  },
];

export const locations: LocationInfo[] = [
  {
    region: "Texas, US",
    clinics: 4,
    highlights: "High-volume same-day primary care and chronic disease programs.",
  },
  {
    region: "Florida, US",
    clinics: 3,
    highlights: "Strong bilingual patient support and specialist consult demand.",
  },
  {
    region: "Georgia, US",
    clinics: 2,
    highlights: "Growing preventive care outreach and multidisciplinary teams.",
  },
  {
    region: "London & Manchester, UK",
    clinics: 3,
    highlights: "Private-pay and NHS-linked services with strong continuity care.",
  },
];
