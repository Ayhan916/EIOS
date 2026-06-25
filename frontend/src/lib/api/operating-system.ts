import apiClient from "./client";

export interface ESGObjective {
  id: string;
  title: string;
  description: string | null;
  category: string;
  objective_status: string;
  target_date: string | null;
  created_at: string;
}

export interface ESGProgram {
  id: string;
  title: string;
  description: string | null;
  program_status: string;
  program_type: string | null;
  owner_user_id: string | null;
  linked_objectives: string[];
  created_at: string;
}

export interface ESGControl {
  id: string;
  control_name: string;
  control_type: string;
  description: string | null;
  control_status: string;
  effectiveness_status: string;
  owner_user_id: string | null;
  linked_program_id: string | null;
  created_at: string;
}

export interface ControlTest {
  id: string;
  control_id: string;
  test_result: string;
  tested_by_user_id: string | null;
  findings: string | null;
  tested_at: string;
  created_at: string;
}

export interface ComplianceOperation {
  id: string;
  framework_name: string;
  coverage_percent: number;
  gap_count: number;
  operation_status: string;
  owner_user_id: string | null;
  last_synced_at: string | null;
  created_at: string;
}

export interface AccountabilityAssignment {
  id: string;
  entity_type: string;
  entity_id: string;
  role: string;
  assigned_to_user_id: string;
  assignment_status: string;
  assigned_at: string;
  created_at: string;
}

export interface CalendarEvent {
  id: string;
  title: string;
  event_type: string;
  event_status: string;
  scheduled_at: string;
  recurrence_rule: string | null;
  reminder_days: number | null;
  linked_entity_type: string | null;
  linked_entity_id: string | null;
  notes: string | null;
  created_at: string;
}

export interface TimelineEntry {
  event_type: string;
  entity_type: string;
  entity_id: string;
  title: string;
  timestamp: string;
  status: string | null;
}

export interface OperatingSystemDashboard {
  objectives_total: number;
  objectives_at_risk: number;
  initiatives_total: number;
  initiatives_at_risk: number;
  actions_total: number;
  actions_overdue: number;
  strategic_risks_total: number;
  strategic_risks_critical: number;
  compliance_operations: number;
  governance_calendar_events: number;
  programs_total: number;
  controls_total: number;
}

export const operatingSystemApi = {
  getDashboard: () =>
    apiClient.get<OperatingSystemDashboard>("/operating-system/dashboard"),

  getTimeline: (limit = 50) =>
    apiClient.get<TimelineEntry[]>(`/operating-system/timeline?limit=${limit}`),

  // Calendar
  listCalendarEvents: (params?: { event_type?: string; event_status?: string; limit?: number }) =>
    apiClient.get<CalendarEvent[]>("/operating-system/calendar", { params }),

  createCalendarEvent: (data: {
    title: string;
    event_type: string;
    scheduled_at: string;
    recurrence_rule?: string;
    reminder_days?: number;
    linked_entity_type?: string;
    linked_entity_id?: string;
    notes?: string;
  }) => apiClient.post<CalendarEvent>("/operating-system/calendar", data),

  // Programs
  listPrograms: (params?: { program_status?: string; program_type?: string; limit?: number }) =>
    apiClient.get<ESGProgram[]>("/operating-system/programs", { params }),

  createProgram: (data: {
    title: string;
    description?: string;
    program_type?: string;
    owner_user_id?: string;
    linked_objectives?: string[];
  }) => apiClient.post<ESGProgram>("/operating-system/programs", data),

  // Controls
  listControls: (params?: { control_type?: string; control_status?: string; linked_program_id?: string; limit?: number }) =>
    apiClient.get<ESGControl[]>("/operating-system/controls", { params }),

  createControl: (data: {
    control_name: string;
    control_type: string;
    description?: string;
    owner_user_id?: string;
    linked_program_id?: string;
  }) => apiClient.post<ESGControl>("/operating-system/controls", data),

  // Control Tests
  listTests: (params?: { control_id?: string; test_result?: string; limit?: number }) =>
    apiClient.get<ControlTest[]>("/operating-system/controls/tests", { params }),

  createTest: (data: {
    control_id: string;
    test_result: string;
    tested_by_user_id?: string;
    findings?: string;
    tested_at?: string;
  }) => apiClient.post<ControlTest>("/operating-system/controls/tests", data),

  // Compliance Operations
  listComplianceOperations: (params?: { framework_name?: string; operation_status?: string; limit?: number }) =>
    apiClient.get<ComplianceOperation[]>("/operating-system/compliance-operations", { params }),

  createComplianceOperation: (data: {
    framework_name: string;
    owner_user_id?: string;
    coverage_percent?: number;
    gap_count?: number;
  }) => apiClient.post<ComplianceOperation>("/operating-system/compliance-operations", data),

  // Accountability
  listAssignments: (params?: { entity_type?: string; entity_id?: string; role?: string; limit?: number }) =>
    apiClient.get<AccountabilityAssignment[]>("/operating-system/accountability/assignments", { params }),

  assignAccountability: (data: {
    entity_type: string;
    entity_id: string;
    role: string;
    assigned_to_user_id: string;
    assigned_by_user_id?: string;
  }) => apiClient.post<AccountabilityAssignment>("/operating-system/accountability/assignments", data),
};
