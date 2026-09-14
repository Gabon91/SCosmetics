export type Treatment = {
  id: number;
  name: string;
  category: string;
  duration_minutes: number;
  price: number | string;
};

export type Package = {
  id: number;
  name: string;
  price: number | string;
  sessions: number;
  validity_days: number;
  treatment_ids: number[];
};

export type Slot = {
  beautician_id: number;
  beautician_name: string;
  start_time: string;
  end_time: string;
};

export type Availability = { slots: Slot[] };

export type User = {
  id: number;
  first_name: string;
  last_name: string;
  email: string;
};

export type Appointment = {
  id: number;
  treatment_id: number;
  beautician_id: number;
  user_package_id: number | null;
  start_time: string;
  end_time: string;
  status: "booked" | "completed" | "cancelled" | "no_show";
};

export type CustomerPackage = {
  id: number;
  package_id: number;
  package_name: string;
  total_sessions: number;
  used_sessions: number;
  remaining_sessions: number;
  expiration_date: string;
  status: "active" | "exhausted";
  expired: boolean;
};

export type Order = {
  id: number;
  total: number | string;
  status: "demo_confirmed";
  created_at: string;
  items: { package_id: number; package_name: string; quantity: number }[];
};

export type WaitlistEntry = {
  id: number;
  treatment_id: number;
  preferred_date: string;
  beautician_id: number | null;
  status: "waiting" | "offered" | "fulfilled" | "cancelled";
  offered_start_time: string | null;
  offer_expires_at: string | null;
  offer_expired: boolean;
};
