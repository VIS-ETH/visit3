import { Alert, Image, Paper, Skeleton, Stack } from "@mantine/core";
import { useDebouncedValue } from "@mantine/hooks";
import { IconAlertTriangle } from "@tabler/icons-react";
import { keepPreviousData, useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import type {
  BookletPageResponse,
  UpdateCompanyProfileRequest,
} from "../../orval/generated/fastAPI.schemas";
import {
  toBookletPageRequest,
  type CompanyProfileFormValues,
} from "../../schemas/companyProfileSchema";

const RENDER_DELAY_MS = 600;
const PAGE_WIDTH = 420;
const PAGE_ASPECT_RATIO = "148.5 / 210";

interface CompanyBookletPageProps {
  scope: string;
  ready: boolean;
  values: CompanyProfileFormValues;
  logoUrl: string | null;
  render: (
    request: UpdateCompanyProfileRequest,
  ) => Promise<BookletPageResponse>;
}

const CompanyBookletPage = ({
  scope,
  ready,
  values,
  logoUrl,
  render,
}: CompanyBookletPageProps) => {
  const { t } = useTranslation();
  const current = JSON.stringify(toBookletPageRequest(values));
  const [request] = useDebouncedValue(current, RENDER_DELAY_MS);
  const { data: page } = useQuery({
    queryKey: ["booklet-page", scope, request, logoUrl],
    queryFn: () => render(JSON.parse(request) as UpdateCompanyProfileRequest),
    enabled: ready && request === current,
    placeholderData: keepPreviousData,
    retry: false,
  });

  return (
    <Stack gap="md" align="center">
      <Paper
        withBorder
        radius="sm"
        w="100%"
        maw={PAGE_WIDTH}
        style={{ overflow: "hidden" }}
      >
        {page ? (
          <Image
            src={`data:image/png;base64,${page.png_base64}`}
            alt={t("company_profile_form.booklet_page_alt")}
          />
        ) : (
          <Skeleton radius={0} style={{ aspectRatio: PAGE_ASPECT_RATIO }} />
        )}
      </Paper>
      {page?.overflow ? (
        <Alert
          icon={<IconAlertTriangle />}
          color="orange"
          w="100%"
          maw={PAGE_WIDTH}
        >
          {t("company_profile_form.booklet_page_overflow")}
        </Alert>
      ) : null}
    </Stack>
  );
};

export default CompanyBookletPage;
