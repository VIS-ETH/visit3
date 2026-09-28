import {
  ActionIcon,
  Alert,
  Button,
  Drawer,
  Group,
  Loader,
  Select,
  Stack,
  Table,
  Text,
} from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { notifications } from "@mantine/notifications";
import { IconAlertCircle, IconEyeCheck, IconTrash } from "@tabler/icons-react";
import { useQueryClient } from "@tanstack/react-query";
import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { getApiErrorCode } from "../../api/errors";
import {
  getGetCompanyUsersQueryKey,
  getSearchCompaniesQueryKey,
  useAcknowledgeCompanyNewMembers,
  useAddCompanyMember,
  useGetCompanyUsers,
  useRemoveCompanyUser,
} from "../../orval/generated/company/company";
import { UserFilter } from "../../orval/generated/fastAPI.schemas";
import {
  getListUsersQueryKey,
  useListUsers,
} from "../../orval/generated/user/user";
import { getDisplayName } from "../../utils/display";
import BookingNewAdditionsBadge from "../bookings/BookingNewAdditionsBadge";

const SEARCH_DEBOUNCE_MS = 300;
const CANDIDATE_PAGE_SIZE = 20;

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
  const [debouncedCandidateSearch] = useDebouncedValue(
    candidateSearch,
    SEARCH_DEBOUNCE_MS,
  );

  useEffect(() => {
    setErrorCode(null);
    setCandidateId(null);
  }, [companyId]);

  const { data: members, isLoading } = useGetCompanyUsers(companyId, {
    query: { enabled: companyId !== "" },
  });

  const { data: candidatePage } = useListUsers(
    {
      query: debouncedCandidateSearch.trim() || undefined,
      filter: UserFilter.company,
      page: 1,
      page_size: CANDIDATE_PAGE_SIZE,
    },
    { query: { enabled: companyId !== "" } },
  );

  const candidates = (candidatePage?.items ?? [])
    .filter((user) => !user.company_id)
    .map((user) => ({
      value: user.id,
      label: `${getDisplayName(user.first_name, user.last_name, user.email)} (${user.email})`,
    }));

  const refresh = async () => {
    await queryClient.invalidateQueries({
      queryKey: getGetCompanyUsersQueryKey(companyId),
    });
    await queryClient.invalidateQueries({ queryKey: getListUsersQueryKey() });
    await queryClient.invalidateQueries({
      queryKey: getSearchCompaniesQueryKey(),
    });
  };

  const { mutate: addMember, isPending: isAdding } = useAddCompanyMember({
    mutation: {
      onSuccess: async () => {
        await refresh();
        setCandidateId(null);
        notifications.show({
          color: "green",
          message: t("company_management.members.added"),
        });
      },
      onError: (error) => {
        setErrorCode(getApiErrorCode(error) ?? "server.error");
      },
    },
  });

  const { mutate: acknowledge, isPending: isAcknowledging } =
    useAcknowledgeCompanyNewMembers({
      mutation: {
        onSuccess: async () => {
          await refresh();
          notifications.show({
            color: "green",
            message: t("company_management.members.acknowledged"),
          });
        },
        onError: (error) => {
          setErrorCode(getApiErrorCode(error) ?? "server.error");
        },
      },
    });

  const hasNewMembers = (members ?? []).some((member) =>
    Boolean(member.new_in_company_since),
  );

  const { mutate: removeMember, isPending: isRemoving } = useRemoveCompanyUser({
    mutation: {
      onSuccess: async () => {
        await refresh();
        notifications.show({
          color: "green",
          message: t("company_management.members.removed"),
        });
      },
      onError: (error) => {
        setErrorCode(getApiErrorCode(error) ?? "server.error");
      },
    },
  });

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
        {errorCode ? (
          <Alert
            color="red"
            icon={<IconAlertCircle />}
            title={t("error.title")}
          >
            {t(errorCode)}
          </Alert>
        ) : null}

        {hasNewMembers ? (
          <Group justify="flex-end">
            <Button
              color="gray"
              leftSection={<IconEyeCheck size={16} />}
              loading={isAcknowledging}
              onClick={() => {
                setErrorCode(null);
                acknowledge({ companyId });
              }}
              size="xs"
              variant="subtle"
            >
              {t("company_management.members.acknowledge")}
            </Button>
          </Group>
        ) : null}

        {isLoading ? (
          <Loader />
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
                  </Table.Td>
                  <Table.Td>{member.email}</Table.Td>
                  <Table.Td w={60}>
                    <ActionIcon
                      aria-label={t("company_management.members.remove")}
                      color="red"
                      disabled={isRemoving}
                      onClick={() => {
                        setErrorCode(null);
                        removeMember({ companyId, userId: member.id });
                      }}
                      variant="light"
                    >
                      <IconTrash size={16} />
                    </ActionIcon>
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
            disabled={!candidateId}
            loading={isAdding}
            onClick={() => {
              if (!candidateId) return;
              setErrorCode(null);
              addMember({ companyId, data: { user_id: candidateId } });
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
