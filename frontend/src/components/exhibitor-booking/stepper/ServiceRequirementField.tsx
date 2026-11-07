import { Button, Group, Paper, Stack, Text, Textarea } from "@mantine/core";
import {
  IconFile,
  IconFileTypePdf,
  IconPhoto,
  IconTrash,
  IconUpload,
  IconVideo,
} from "@tabler/icons-react";
import { useTranslation } from "react-i18next";
import { KpEventServiceRequirementType } from "../../../orval/generated/fastAPI.schemas";
import type { ServiceRequirementResponse } from "../../../orval/generated/fastAPI.schemas";
import { REQUIREMENT_TEXT_MAX_LENGTH } from "../../../utils/kp-utils";
import {
  acceptForRequirement,
  allowedFormatsLabel,
} from "../../../utils/upload-formats";
import {
  requirementTypeLabel,
  requirementUploadLabel,
} from "../../../utils/requirement-type";
import RepickableFileButton from "../../RepickableFileButton";
import type { DraftBookingRequirementValue } from "../KpBookingSummaryStep";

const iconForRequirement = (type: KpEventServiceRequirementType) => {
  if (type === KpEventServiceRequirementType.image)
    return <IconPhoto size={16} />;
  if (type === KpEventServiceRequirementType.pdf) {
    return <IconFileTypePdf size={16} />;
  }
  if (type === KpEventServiceRequirementType.video)
    return <IconVideo size={16} />;
  return <IconFile size={16} />;
};

interface ServiceRequirementFieldProps {
  requirement: ServiceRequirementResponse;
  value: DraftBookingRequirementValue | undefined;
  onChange: (value: DraftBookingRequirementValue) => void;
}

const RequirementInput = ({
  requirement,
  value,
  onChange,
}: ServiceRequirementFieldProps) => {
  const { t } = useTranslation();
  if (requirement.type === KpEventServiceRequirementType.text) {
    return (
      <Textarea
        label={requirement.name}
        description={requirement.description}
        maxLength={REQUIREMENT_TEXT_MAX_LENGTH}
        minRows={3}
        value={value?.text ?? ""}
        onChange={(event) => onChange({ text: event.currentTarget.value })}
      />
    );
  }
  return (
    <Stack gap={4}>
      <Text size="sm" fw={500}>
        {requirement.name}
      </Text>
      <Text size="xs" c="dimmed">
        {requirement.description}
      </Text>
      <Text size="xs" c="dimmed">
        {allowedFormatsLabel(requirement.type, t)}
      </Text>
      <Group gap="xs" wrap="nowrap">
        <RepickableFileButton
          accept={acceptForRequirement(requirement.type)}
          onChange={(file) => onChange({ file })}
        >
          {(props) => (
            <Button
              {...props}
              leftSection={<IconUpload size={16} />}
              variant={value?.file ? "default" : "light"}
            >
              {value?.file
                ? t("kp.booking.requirement_replace_file")
                : requirementUploadLabel(requirement.type, t)}
            </Button>
          )}
        </RepickableFileButton>
        {value?.file ? (
          <>
            <Text size="sm" truncate="end">
              {value.file.name}
            </Text>
            <Button
              color="red"
              leftSection={<IconTrash size={16} />}
              onClick={() => onChange({ file: null })}
              variant="subtle"
            >
              {t("kp.booking.requirement_clear_file")}
            </Button>
          </>
        ) : null}
      </Group>
    </Stack>
  );
};

const ServiceRequirementField = (props: ServiceRequirementFieldProps) => {
  const { t } = useTranslation();
  return (
    <Paper withBorder radius="sm" p="sm">
      <Group gap="xs" mb="xs">
        {iconForRequirement(props.requirement.type)}
        <Text size="xs" c="dimmed">
          {requirementTypeLabel(props.requirement.type, t)}
        </Text>
      </Group>
      <RequirementInput {...props} />
    </Paper>
  );
};

export default ServiceRequirementField;
