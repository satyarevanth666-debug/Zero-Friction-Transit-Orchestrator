export type Mode = "rail" | "bus" | "flight" | "transfer";

export type TruthLevel =
  | "OFFICIAL_TIMETABLE"
  | "COMMUNITY_GTFS"
  | "LIVE_API"
  | "ESTIMATED"
  | "USER_PROVIDED"
  | "UNKNOWN";

export type AvailabilityStatus = "CNF" | "RAC" | "WL" | "UNKNOWN";

export interface Leg {
  id: string;
  mode: Mode;
  operator: string;
  service_number: string;
  service_name: string;
  from_station_code: string;
  from_station_name: string;
  to_station_code: string;
  to_station_name: string;
  departure_time: string;
  arrival_time: string;
  duration_minutes: number;
  class_code?: string;
  fare_inr: number | null;
  fare_truth_level: TruthLevel;
  schedule_truth_level: TruthLevel;
  availability_status: AvailabilityStatus;
  waitlist_position?: number;
  waitlist_chance?: "Low" | "Medium" | "High";
  platform?: string;
}

export interface Layover {
  at_station_code: string;
  at_station_name: string;
  duration_minutes: number;
  instructions: string;
  is_tight: boolean;
}

export interface Itinerary {
  id: string;
  legs: Leg[];
  layovers: Layover[];
  total_duration_minutes: number;
  departure_time: string;
  arrival_time: string;
  known_fare_inr: number;
  unknown_fare_legs: number;
  is_budget_verified: boolean;
  reliability_score: number;
  tag: "Best Balance" | "Cheapest" | "Fastest" | "Most Reliable";
  why_this: string;
  warnings: string[];
}
