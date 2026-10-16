import { useState, type FormEvent } from "react";

interface AnswerInputProps {
  disabled?: boolean;
  onSubmit: (value: string) => void;
}

export function AnswerInput({ disabled = false, onSubmit }: AnswerInputProps) {
  const [value, setValue] = useState("");

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!value.trim()) return;
    onSubmit(value);
    setValue("");
  }

  return (
    <form className="answer-form" onSubmit={handleSubmit}>
      <label htmlFor="answer">Country</label>
      <div className="answer-row">
        <input
          id="answer"
          autoComplete="off"
          autoFocus
          disabled={disabled}
          value={value}
          onChange={(event) => setValue(event.target.value)}
          placeholder="Type a country name or code"
        />
        <button type="submit" disabled={disabled || !value.trim()}>
          Submit
        </button>
      </div>
    </form>
  );
}
