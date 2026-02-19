import {
	Alert,
	Button,
	Center,
	Group,
	Loader,
	Modal,
	Paper,
	Stack,
	Table,
	Text,
	Title,
} from "@mantine/core";
import { IconAlertCircle, IconTrash } from "@tabler/icons-react";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { useQueryClient } from "@tanstack/react-query";
import { isAdmin, isStaff } from "../api/utils";
import {
	getListCompaniesWithUsersQueryKey,
	useDeleteCompanyKeepUsers,
	useDeleteCompanyWithUsers,
	useListCompaniesWithUsers,
} from "../orval/generated/company/company";
import type { CompanyAssignedUserResponse } from "../orval/generated/fastAPI.schemas";

interface CompanyForDelete {
	id: string;
	name: string;
	usersCount: number;
}

function getDisplayName(user: CompanyAssignedUserResponse): string {
	const fullName = `${user.first_name ?? ""} ${user.last_name ?? ""}`.trim();
	return fullName.length > 0 ? fullName : "-";
}

export default function CompanyManagement() {
	const { t } = useTranslation();
	const queryClient = useQueryClient();
	const adminStatus = isAdmin();
	const staffStatus = isStaff();
	const [deleteModalOpened, setDeleteModalOpened] = useState(false);
	const [companyToDelete, setCompanyToDelete] = useState<CompanyForDelete | null>(
		null,
	);
	const {
		data: companies,
		isLoading,
		isError,
	} = useListCompaniesWithUsers({
		query: {
			enabled: staffStatus,
		},
	});

	const {
		mutate: deleteCompanyKeepUsers,
		isPending: isDeletingKeepUsers,
		isError: isDeleteKeepUsersError,
	} = useDeleteCompanyKeepUsers({
		mutation: {
			onSuccess: () => {
				queryClient.invalidateQueries({
					queryKey: getListCompaniesWithUsersQueryKey(),
				});
				setDeleteModalOpened(false);
			},
		},
	});

	const {
		mutate: deleteCompanyWithUsers,
		isPending: isDeletingWithUsers,
		isError: isDeleteWithUsersError,
	} = useDeleteCompanyWithUsers({
		mutation: {
			onSuccess: () => {
				queryClient.invalidateQueries({
					queryKey: getListCompaniesWithUsersQueryKey(),
				});
				setDeleteModalOpened(false);
			},
		},
	});

	const isDeleting = isDeletingKeepUsers || isDeletingWithUsers;

	const handleOpenDeleteModal = (
		companyId: string,
		companyName: string,
		usersCount: number,
	) => {
		if (!adminStatus) return;
		setCompanyToDelete({
			id: companyId,
			name: companyName,
			usersCount,
		});
		setDeleteModalOpened(true);
	};

	const handleDeleteKeepUsers = () => {
		if (!adminStatus) return;
		if (!companyToDelete?.id) return;
		deleteCompanyKeepUsers({ companyId: companyToDelete.id });
	};

	const handleDeleteWithUsers = () => {
		if (!adminStatus) return;
		if (!companyToDelete?.id) return;
		deleteCompanyWithUsers({ companyId: companyToDelete.id });
	};

	const companyHasUsers = (companyToDelete?.usersCount ?? 0) > 0;

	return (
		<Center h="100%" w="100%" py="xl">
			<Stack w="100%" maw={1100} gap="lg">
				<Title order={2}>{t("company_management.title")}</Title>

				<Modal
					opened={adminStatus && deleteModalOpened}
					onClose={() => {
						if (!isDeleting) {
							setDeleteModalOpened(false);
						}
					}}
					onExitTransitionEnd={() => {
						if (!deleteModalOpened) {
							setCompanyToDelete(null);
						}
					}}
					closeOnClickOutside={!isDeleting}
					closeOnEscape={!isDeleting}
					withCloseButton={!isDeleting}
					title={t("company_management.delete_modal.title")}
					centered
				>
					<Stack gap="sm">
						<Text>
							{t("company_management.delete_modal.message", {
								name: companyToDelete?.name ?? "-",
							})}
						</Text>
						<Text c="red" fw={600}>
							{t("company_management.delete_modal.irreversible")}
						</Text>
						<Group justify="flex-end" mt="md">
							<Button
								variant="default"
								onClick={() => setDeleteModalOpened(false)}
								disabled={isDeleting}
							>
								{t("company_management.delete_modal.cancel")}
							</Button>
							{companyHasUsers ? (
								<>
									<Button
										color="orange"
										onClick={handleDeleteKeepUsers}
										loading={isDeletingKeepUsers}
										disabled={!companyToDelete?.id || isDeleting}
									>
										{t("company_management.delete_modal.keep_users")}
									</Button>
									<Button
										color="red"
										onClick={handleDeleteWithUsers}
										loading={isDeletingWithUsers}
										disabled={!companyToDelete?.id || isDeleting}
									>
										{t("company_management.delete_modal.delete_with_users")}
									</Button>
								</>
							) : (
								<Button
									color="red"
									onClick={handleDeleteKeepUsers}
									loading={isDeletingKeepUsers}
									disabled={!companyToDelete?.id || isDeleting}
								>
									{t("company_management.delete")}
								</Button>
							)}
						</Group>
					</Stack>
				</Modal>

				{adminStatus && (isDeleteKeepUsersError || isDeleteWithUsersError) && (
					<Alert icon={<IconAlertCircle />} color="red" title={t("server.error")}>
						{t("company_management.delete_error")}
					</Alert>
				)}

				{isLoading ? (
					<Center py="xl">
						<Loader />
					</Center>
				) : isError ? (
					<Alert icon={<IconAlertCircle />} color="red" title={t("server.error")}>
						{t("company_management.error")}
					</Alert>
				) : companies && companies.length > 0 ? (
					companies.map((company) => (
						<Paper key={company.id} withBorder p="md" radius="md">
							<Stack gap="sm">
								<Group justify="space-between" align="center">
									<Title order={4}>{company.name}</Title>
									{adminStatus ? (
										<Button
											leftSection={<IconTrash size={14} />}
											size="xs"
											color="red"
											variant="light"
											onClick={() =>
												handleOpenDeleteModal(
														company.id,
														company.name,
														company.users.length,
													)
											}
										>
											{t("company_management.delete")}
										</Button>
									) : null}
								</Group>

								{company.users.length > 0 ? (
									<Table striped highlightOnHover withTableBorder>
										<Table.Thead>
											<Table.Tr>
												<Table.Th>{t("company_management.user_name")}</Table.Th>
												<Table.Th>{t("company_management.user_email")}</Table.Th>
												<Table.Th>{t("company_management.user_phone")}</Table.Th>
											</Table.Tr>
										</Table.Thead>
										<Table.Tbody>
											{company.users.map((user) => (
												<Table.Tr key={user.id}>
													<Table.Td>{getDisplayName(user)}</Table.Td>
													<Table.Td>{user.email}</Table.Td>
													<Table.Td>{user.phone_number ?? "-"}</Table.Td>
												</Table.Tr>
											))}
										</Table.Tbody>
									</Table>
								) : (
									<Text c="dimmed">{t("company_management.no_users")}</Text>
								)}
							</Stack>
						</Paper>
					))
				) : (
					<Alert
						icon={<IconAlertCircle />}
						color="blue"
						title={t("company_management.no_companies")}
					>
						{t("company_management.no_companies_description")}
					</Alert>
				)}
			</Stack>
		</Center>
	);
}
