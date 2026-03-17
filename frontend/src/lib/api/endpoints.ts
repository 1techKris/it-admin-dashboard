// frontend/src/lib/api/endpoints.ts

export const endpoints = {
  // Servers (devices)
  servers: {
    list: (
      q?: string,
      status?: string,
      page?: number,
      include_archived?: boolean
    ) =>
      `/servers?q=${encodeURIComponent(q || "")}` +
      `&status=${encodeURIComponent(status || "all")}` +
      `&page=${page || 1}` +
      `&include_archived=${!!include_archived}`,
    archive: (device_id: string) => `/servers/${encodeURIComponent(device_id)}`,
    restore: (device_id: string) => `/servers/${encodeURIComponent(device_id)}/restore`,
  },

  // Printers (SNMP)
  printers: {
    list: (include_archived?: boolean) =>
      `/printers?include_archived=${!!include_archived}`,
    add: `/printers`,
    archive: (id: number) => `/printers/${id}`,
    restore: (id: number) => `/printers/${id}/restore`,
    detail: (id: number) => `/printers/${id}`,
    refresh: (id: number) => `/printers/${id}/refresh`,
    wsPath: (id: number) => `/printers/ws/${id}`,
  },

  // Network scanner
  network: {
    start: `/network/scan`,
    status: (id: string) => `/network/scan/${id}`,
    wsScanPath: (id: string) => `/network/ws/scan/${id}`,
    import: (id: string) => `/network/scan/${id}/import`,
  },

  // Active Directory
  ad: {
    // Users
    users: (
      q?: string,
      enabled?: string,
      locked?: string,
      page?: number,
      page_size?: number
    ) =>
      `/ad/users?q=${encodeURIComponent(q || "")}` +
      `&enabled=${enabled ?? ""}` +
      `&locked=${locked ?? ""}` +
      `&page=${page || 1}&page_size=${page_size || 50}`,
    reset: (dn: string) => `/ad/users/${encodeURIComponent(dn)}/reset-password`,
    disable: (dn: string) => `/ad/users/${encodeURIComponent(dn)}/disable`,
    enable: (dn: string) => `/ad/users/${encodeURIComponent(dn)}/enable`,
    unlock: (dn: string) => `/ad/users/${encodeURIComponent(dn)}/unlock`,
    move: (dn: string) => `/ad/users/${encodeURIComponent(dn)}/move`,

    // Groups
    groups: (q?: string, page?: number, page_size?: number) =>
      `/ad/groups?q=${encodeURIComponent(q || "")}&page=${page || 1}&page_size=${page_size || 50}`,
    groupMembers: (dn: string) => `/ad/groups/${encodeURIComponent(dn)}/members`,
    groupAddMember: (dn: string) => `/ad/groups/${encodeURIComponent(dn)}/members/add`,
    groupRemoveMember: (dn: string) => `/ad/groups/${encodeURIComponent(dn)}/members/remove`,

    // Computers
    computers: (q?: string, page?: number, page_size?: number) =>
      `/ad/computers?q=${encodeURIComponent(q || "")}&page=${page || 1}&page_size=${page_size || 50}`,

    // OU Tree + Debug
    ouTree: `/ad/ou-tree`,
    ouTreeMin: `/ad/ou-tree/min`,
    debug: `/ad/debug`,
  },

  // Settings
  settings: {
    teamsTest: `/settings/teams/test`,
    adGet: `/settings/ad`,
    adPut: `/settings/ad`,
    adTest: `/settings/ad/test`,
  },

  // Alerts
  alerts: {
    list: `/alerts`,
    ack: (id: string) => `/alerts/${id}/ack`,
  },
};