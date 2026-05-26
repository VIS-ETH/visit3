import { useQuery } from "@tanstack/react-query";
import type { ServiceResponse } from "../orval/generated/fastAPI.schemas";
import { customInstance } from "./mutator";

export const getListAvailableServicesQueryKey = (eventId: string) => [
  `/api/kp/events/${eventId}/services/available`,
];

export const listAvailableServices = (
  eventId: string,
  signal?: AbortSignal,
) =>
  customInstance<ServiceResponse[]>({
    url: `/api/kp/events/${eventId}/services/available`,
    method: "GET",
    signal,
  });

export const useListAvailableServices = (eventId: string) =>
  useQuery({
    queryKey: getListAvailableServicesQueryKey(eventId),
    queryFn: ({ signal }) => listAvailableServices(eventId, signal),
    enabled: Boolean(eventId),
  });
