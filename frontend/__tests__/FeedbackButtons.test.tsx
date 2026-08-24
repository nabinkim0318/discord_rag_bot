import { fireEvent, render, screen } from "@testing-library/react";
import FeedbackButtons from "../pages/FeedbackButtons";

describe("FeedbackButtons", () => {
  it("does not submit like/dislike without a query ID", () => {
    const onFeedback = jest.fn();
    render(<FeedbackButtons onFeedback={onFeedback} queryId={null} />);

    fireEvent.click(screen.getByLabelText("Thumbs up"));
    fireEvent.click(screen.getByLabelText("Thumbs down"));
    expect(onFeedback).not.toHaveBeenCalled();
    expect(
      screen.getByText("Feedback unavailable for this reply."),
    ).toBeInTheDocument();
  });

  it("submits like and dislike when a query ID is present", () => {
    const onFeedback = jest.fn();
    render(<FeedbackButtons onFeedback={onFeedback} queryId="qid-1" />);

    fireEvent.click(screen.getByLabelText("Thumbs up"));
    fireEvent.click(screen.getByLabelText("Thumbs down"));
    expect(onFeedback).toHaveBeenCalledWith("like");
    expect(onFeedback).toHaveBeenCalledWith("dislike");
  });

  it("prevents duplicate clicks while submitting or after success", () => {
    const onFeedback = jest.fn();
    const { rerender } = render(
      <FeedbackButtons
        onFeedback={onFeedback}
        queryId="qid-1"
        status="submitting"
      />,
    );
    fireEvent.click(screen.getByLabelText("Thumbs up"));
    expect(onFeedback).not.toHaveBeenCalled();

    rerender(
      <FeedbackButtons
        onFeedback={onFeedback}
        queryId="qid-1"
        disabled
        status="success"
      />,
    );
    fireEvent.click(screen.getByLabelText("Thumbs down"));
    expect(onFeedback).not.toHaveBeenCalled();
    expect(screen.getByText("Thanks for the feedback.")).toBeInTheDocument();
  });

  it("shows failure state", () => {
    render(
      <FeedbackButtons onFeedback={jest.fn()} queryId="qid-1" status="error" />,
    );
    expect(screen.getByText("Could not save feedback.")).toBeInTheDocument();
  });

  it("retry remains available even when feedback is disabled", () => {
    const onFeedback = jest.fn();
    render(
      <FeedbackButtons
        onFeedback={onFeedback}
        queryId="qid-1"
        disabled
        status="success"
      />,
    );
    fireEvent.click(screen.getByLabelText("Retry"));
    expect(onFeedback).toHaveBeenCalledWith("retry");
  });
});
