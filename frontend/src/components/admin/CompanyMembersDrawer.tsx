import {
  ActionIcon,
  Anchor,
  Button,
  Drawer,
  Group,
  Select,
  Stack,
  Table,
  Text,
  Tooltip,
} from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { notifySuccess } from "../../utils/notify";
import {
  IconEyeCheck,
  IconPencil,
  IconTrash,
  IconUserSearch,
} from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link } from "react-router";
import { getInlineErrorCode, inlineErrorRequest } from "../../api/errors";
import {
  getGetCompanyUsersQueryKey,
  getSearchCompaniesQueryKey,
  useAcknowledgeCompanyNewMembers,
  useAddCompanyMember,
  useGetCompanyUsers,
  useRemoveCompanyUser,
} from "../../orval/generated/company/company";
import type { UserResponse } from "../../orval/generated/fastAPI.schemas";
import { getListUsersQueryKey } from "../../orval/generated/user/user";
import { getDisplayName } from "../../utils/display";
import BookingNewAdditionsBadge from "../staff-bookings/BookingNewAdditionsBadge";
import { useCurrentUser } from "../../context/useCurrentUser";
import UserEditDrawer from "./UserEditDrawer";
import { useImpersonate } from "./useImpersonate";
import { useMemberCandidates } from "./useMemberCandidates";
import { useAsyncAction } from "../../hooks/use-async-action";
import ErrorAlert from "../ErrorAlert";
import PageLoader from "../PageLoader";

const SEARCH_DEBOUNCE_MS = 300;

interface CompanyMembersDrawerProps {
  company: { id: string; name: string } | null;
  onClose: () => void;
}

const CompanyMembersDrawer = ({
  company,
  onClose,
}: CompanyMembersDrawerProps) => {
  const { t } = useTranslation();
  const queryClient = useQueryClient();
  const companyId = company?.id ?? "";
  const [errorCode, setErrorCode] = useState<string | null>(null);
  const [candidateId, setCandidateId] = useState<string | null>(null);
  const [candidateSearch, setCandidateSearch] = useState("");
  const [editedUser, setEditedUser] = useState<UserResponse | null>(null);
  const { canImpersonate, canImpersonateUser, impersonate } = useImpersonate();
  const isAdmin = useCurrentUser().user?.is_admin ?? false;
  const [debouncedCandidateSearch] = useDebouncedValue(
    candidateSearch,
    SEARCH_DEBOUNCE_MS,
  );

  useEffect(() => {
    setErrorCode(null);
    setCandidateId(null);
  }, [companyId]);

  const {
    data: members,
    isLoading,
    isError,
  } = useGetCompanyUsers(companyId, {
    query: { enabled: companyId !== "" },
  });

  const { data: unassignedUsers } = useMemberCandidates(
    debouncedCandidateSearch,
    companyId !== "",
  );

  const candidates = (unassignedUsers ?? []).map((user) => ({
    value: user.id,
    label: `${getDisplayName(user.first_name, user.last_name, user.email)} (${user.email})`,
  }));

  const refresh = () =>
    Promise.all([
      queryClient.invalidateQueries({
        queryKey: getGetCompanyUsersQueryKey(companyId),
      }),
      queryClient.invalidateQueries({ queryKey: getListUsersQueryKey() }),
      queryClient.invalidateQueries({ queryKey: getSearchCompaniesQueryKey() }),
    ]);

  const { mutateAsync: addMember } = useAddCompanyMember({
    request: inlineErrorRequest,
  });
  const { mutateAsync: acknowledge } = useAcknowledgeCompanyNewMembers({
    request: inlineErrorRequest,
  });
  const { mutateAsync: removeMember } = useRemoveCompanyUser({
    request: inlineErrorRequest,
  });

  const [activeAction, setActiveAction] = useState<string | null>(null);
  const { run: runMemberAction, isRunning } = useAsyncAction(
    async (key: string, action: () => Promise<unknown>, successKey: string) => {
      setActiveAction(key);
      setErrorCode(null);
      await action();
      await refresh();
      notifySuccess(t(successKey));
    },
    (error) => setErrorCode(getInlineErrorCode(error)),
  );
  const isActive = (key: string) => isRunning && activeAction === key;

  const hasNewMembers = (members ?? []).some((member) =>
    Boolean(member.new_in_company_since),
  );

  return (
    <Drawer
      onClose={onClose}
      opened={company !== null}
      position="right"
      title={t("company_management.members.title", {
        name: company?.name ?? "",
      })}
    >
      <Stack gap="md">
        {errorCode ? <ErrorAlert>{t(errorCode)}</ErrorAlert> : null}

        <UserEditDrawer
          canEditPrivileges={isAdmin}
          onClose={() => {
            setEditedUser(null);
            void refresh();
          }}
          user={editedUser}
        />

        <Group justify="space-between">
          <Anchor
            component={Link}
            size="sm"
            to={`/user-management?${new URLSearchParams({
              query: company?.name ?? "",
            }).toString()}`}
          >
            {t("company_management.members.open_in_user_management")}
          </Anchor>
          {hasNewMembers ? (
            <Button
              color="gray"
              leftSection={<IconEyeCheck size={16} />}
              disabled={isRunning}
              loading={isActive("acknowledge")}
              onClick={() =>
                void runMemberAction(
                  "acknowledge",
                  () => acknowledge({ companyId }),
                  "company_management.members.acknowledged",
                )
              }
              size="xs"
              variant="subtle"
            >
              {t("company_management.members.acknowledge")}
            </Button>
          ) : null}
        </Group>

        {isLoading ? (
          <PageLoader />
        ) : isError ? (
          <ErrorAlert />
        ) : members && members.length > 0 ? (
          <Table highlightOnHover>
            <Table.Tbody>
              {members.map((member) => (
                <Table.Tr key={member.id}>
                  <Table.Td>
                    <Group gap="xs" wrap="nowrap">
                      {getDisplayName(member.first_name, member.last_name)}
                      {member.new_in_company_since ? (
                        <BookingNewAdditionsBadge />
                      ) : null}
                    </Group>
                    <Text c="dimmed" size="xs">
                      {member.email}
                    </Text>
                  </Table.Td>
                  <Table.Td>
                    <Group gap="xs" justify="flex-end" wrap="nowrap">
                      {canImpersonate ? (
                        <Tooltip label={t("user_management.impersonate")}>
                          <ActionIcon
                            aria-label={t("user_management.impersonate")}
                            color="blue"
                            disabled={!canImpersonateUser(member)}
                            onClick={() => impersonate(member)}
                            variant="light"
                          >
                            <IconUserSearch size={16} />
                          </ActionIcon>
                        </Tooltip>
                      ) : null}
                      <Tooltip label={t("user_management.edit.title")}>
                        <ActionIcon
                          aria-label={t("user_management.edit.title")}
                          onClick={() => setEditedUser(member)}
                          variant="light"
                        >
                          <IconPencil size={16} />
                        </ActionIcon>
                      </Tooltip>
                      <Tooltip label={t("company_management.members.remove")}>
                        <ActionIcon
                          aria-label={t("company_management.members.remove")}
                          color="red"
                          disabled={isRunning}
                          loading={isActive(member.id)}
                          onClick={() =>
                            void runMemberAction(
                              member.id,
                              () =>
                                removeMember({ companyId, userId: member.id }),
                              "company_management.members.removed",
                            )
                          }
                          variant="light"
                        >
                          <IconTrash size={16} />
                        </ActionIcon>
                      </Tooltip>
                    </Group>
                  </Table.Td>
                </Table.Tr>
              ))}
            </Table.Tbody>
          </Table>
        ) : (
          <Text c="dimmed">{t("company_management.members.empty")}</Text>
        )}

        <Select
          clearable
          data={candidates}
          label={t("company_management.members.add")}
          nothingFoundMessage={t("company_management.members.add_empty")}
          onChange={setCandidateId}
          onSearchChange={setCandidateSearch}
          placeholder={t("company_management.members.add_placeholder")}
          searchable
          value={candidateId}
        />
        <Group justify="flex-end">
          <Button
            disabled={!candidateId || isRunning}
            loading={isActive("add")}
            onClick={() => {
              if (!candidateId) return;
              void runMemberAction(
                "add",
                async () => {
                  await addMember({
                    companyId,
                    data: { user_id: candidateId },
                  });
                  setCandidateId(null);
                },
                "company_management.members.added",
              );
            }}
          >
            {t("company_management.members.add_submit")}
          </Button>
        </Group>
      </Stack>
    </Drawer>
  );
};

export default CompanyMembersDrawer;
