import { Text } from "@mantine/core";
import BookingActionModal from "./BookingActionModal";

const BookingConfirmModal = ({
  body,
  onConfirm,
  ...props
}: {
  body: string;
  color?: string;
  onClose: () => void;
  onConfirm: () => Promise<unknown> | void;
  opened: boolean;
  submitLabel: string;
  title: string;
}) => (
  <BookingActionModal {...props} onSubmit={onConfirm}>
    {() => <Text size="sm">{body}</Text>}
  </BookingActionModal>
);

export default BookingConfirmModal;
