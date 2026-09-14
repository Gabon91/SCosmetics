export type StaffUser = {
  id: number;
  first_name: string;
  last_name: string;
  role: "admin" | "beautician" | "customer";
};

export type Customer = {
  id: number; first_name: string; last_name: string; email: string; phone: string;
  role: "customer"; active: boolean; created_at: string;
};

export type StaffAppointment = {
  id: number;
  customer_id: number;
  customer_name: string;
  customer_phone: string;
  beautician_id: number;
  beautician_name: string;
  treatment_id: number;
  treatment_name: string;
  start_time: string;
  end_time: string;
  status: "booked" | "completed" | "cancelled" | "no_show";
  uses_package: boolean;
};

export type Dashboard = {
  date: string;
  appointments_today: number;
  completed_today: number;
  upcoming_today: number;
  active_customers: number | null;
  demo_orders_month: number | null;
  demo_sales_month: string | null;
  appointments: StaffAppointment[];
};

export type Beautician = { id: number; name: string };

export type WorkingHours = { weekday: number; start_time: string; end_time: string };
export type BookableBeautician = {
  id: number; user_id: number; first_name: string; last_name: string;
  email: string; phone: string; bio: string; active: boolean;
  treatment_ids: number[]; working_hours: WorkingHours[];
};

export type Treatment = {
  id: number;
  name: string;
  category: string;
  description: string;
  duration_minutes: number;
  price: string | number;
  accent: string;
  active: boolean;
};

export type Package = {
  id: number;
  name: string;
  price: string | number;
  sessions: number;
  validity_days: number;
  treatment_ids: number[];
  active: boolean;
};

export type Equipment = {
  id: number;
  name: string;
  manufacturer: string;
  description: string;
  image_url: string;
  treatment_ids: number[];
  active: boolean;
};

export type TeamMember = {
  id: number;
  name: string;
  title: string;
  description: string;
  image_url: string;
  featured: boolean;
  display_order: number;
  active: boolean;
};
