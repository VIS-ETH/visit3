import { useState } from "react";
import {
  Button,
  TextInput,
  PasswordInput,
  Paper,
  Stack,
  Center,
  Title,
  Text,
} from "@mantine/core";
import { notifications } from "@mantine/notifications";
import { IconMailSearch, IconLock, IconPhone } from "@tabler/icons-react";
import { useNavigate } from "react-router";
import { useDocumentTitle } from "@mantine/hooks";
import { registerSchema } from "../schemas/registerSchema";
import { useTranslation } from "react-i18next";
import { useTranslatedForm } from "../utils/translator";
import BackButton from "../components/BackButton";
import SearchDropdown from "../components/SearchDropdown";
import { useRegisterUser } from "../orval/generated/auth/auth";
import {
  useCreateCompany,
  useListCompanies,
} from "../orval/generated/company/company";

const Register = () => {
  const { t } = useTranslation();
  useDocumentTitle(t("register.title"));
  const navigate = useNavigate();
  const [companyQuery, setCompanyQuery] = useState("");

  const { mutate: register, isPending } = useRegisterUser({
    mutation: {
      onSuccess: () => {
        navigate("/login");
      },
    },
  });

  const {
    data: companies = [],
    isLoading: companiesLoading,
    refetch: refetchCompanies,
  } = useListCompanies();

  const { mutate: createCompany, isPending: isCreatingCompany } = useCreateCompany({
    mutation: {
      onSuccess: async (company) => {
        if (!company.id) {
          notifications.show({
            color: "red",
            title: t("register.fail"),
            message: t("server.error"),
            autoClose: 4000,
          });
          return;
        }

        form.setFieldValue("companyId", company.id);
        form.setFieldValue("companyName", "");
        setCompanyQuery(company.name);
        await refetchCompanies();
      },
    },
  });

  const form = useTranslatedForm<typeof registerSchema>(registerSchema, {
    initialValues: {
      email: "",
      password: "",
      confirmPassword: "",
      firstName: "",
      lastName: "",
      companyId: "",
      companyName: "",
      phoneNumber: "",
    },
  });

  const normalizedCompanyQuery = companyQuery.trim().toLowerCase();
  const filteredCompanies = companies.filter(
    (company) =>
      Boolean(company.id) &&
      company.name.toLowerCase().includes(normalizedCompanyQuery),
  );

  const showCompanySuggestions =
    normalizedCompanyQuery.length > 0 && !form.values.companyId;

  const handleCreateCompany = () => {
    const name = companyQuery.trim();
    if (!name) {
      return;
    }

    createCompany({
      data: { name },
    });
  };

  return (
    <>
      <BackButton to="/login" />
      <Center py="xl">
        <Stack align="center" gap="xl" maw={600} w="90%" px="md">
          <div>
            <Title ta="center" order={1}>
              {t("register.title")}
            </Title>
            <Text ta="center" c="dimmed" size="sm">
              {t("welcome")}
            </Text>
          </div>

          <Paper w="100%" p="xl" radius="md" withBorder>
            <form
              onSubmit={form.onSubmit((values) => {
                const companyId = values.companyId?.trim() || undefined;
                const companyName = values.companyName?.trim() || undefined;
                register({
                  data: {
                    email: values.email,
                    password: values.password,
                    first_name: values.firstName?.trim(),
                    last_name: values.lastName?.trim(),
                    company_id: companyId,
                    company_name: companyName,
                    phone_number: values.phoneNumber?.trim() || undefined,
                  },
                });
              })}
            >
              <Stack gap="md">
                <TextInput
                  label={t("register.first_name")}
                  withAsterisk
                  autoComplete="given-name"
                  placeholder={t("register.first_name_placeholder")}
                  {...form.getInputProps("firstName")}
                />
                <TextInput
                  label={t("register.last_name")}
                  withAsterisk
                  autoComplete="family-name"
                  placeholder={t("register.last_name_placeholder")}
                  {...form.getInputProps("lastName")}
                />
                <TextInput
                  label={t("register.phone_number")}
                  autoComplete="tel"
                  placeholder={t("register.phone_number_placeholder")}
                  leftSection={<IconPhone size={16} />}
                  {...form.getInputProps("phoneNumber")}
                />
                <TextInput
                  label={t("email.title")}
                  withAsterisk
                  autoComplete="email"
                  placeholder={t("register.email.placeholder")}
                  leftSection={<IconMailSearch size={16} />}
                  {...form.getInputProps("email")}
                />
                <PasswordInput
                  label={t("register.password.title")}
                  withAsterisk
                  autoComplete="new-password"
                  placeholder="************"
                  leftSection={<IconLock size={16} />}
                  {...form.getInputProps("password")}
                />
                <PasswordInput
                  label={t("register.password.confirm")}
                  withAsterisk
                  autoComplete="new-password"
                  placeholder="************"
                  leftSection={<IconLock size={16} />}
                  {...form.getInputProps("confirmPassword")}
                />
                <SearchDropdown
                  label={t("register.company.select")}
                  placeholder={t("register.company.select_placeholder")}
                  withAsterisk
                  error={form.errors.companyId ?? form.errors.companyName}
                  isLoading={companiesLoading}
                  visible={showCompanySuggestions}
                  items={filteredCompanies}
                  query={companyQuery}
                  createLabel={t("register.company.add")}
                  isCreating={isCreatingCompany}
                  onQueryChange={(value) => {
                    setCompanyQuery(value);
                    form.setFieldValue("companyId", "");
                    form.setFieldValue("companyName", value);
                  }}
                  onSelect={(item) => {
                    if (!item.id) {
                      return;
                    }

                    form.setFieldValue("companyId", item.id);
                    form.setFieldValue("companyName", "");
                    setCompanyQuery(item.name);
                  }}
                  onCreate={handleCreateCompany}
                />
                <Button
                  type="submit"
                  loading={isPending}
                  disabled={isPending}
                  size="md"
                >
                  {t("register.button")}
                </Button>
              </Stack>
            </form>
          </Paper>
        </Stack>
      </Center>
    </>
  );
};

export default Register;
