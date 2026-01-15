import { Book } from "@/types";
import { sampleBooks } from "@/data/sampleBooks";
import { cloudfrontBooks } from "@/config/books";

export const fetchBooks = async (): Promise<Book[]> => {
  return cloudfrontBooks.length > 0 ? cloudfrontBooks : sampleBooks;
};

export const fetchBook = async (bookId: string): Promise<Book | null> => {
  // First try CloudFront books
  const cloudfrontBook = cloudfrontBooks.find(b => b.id === bookId);
  if (cloudfrontBook) return cloudfrontBook;
  
  // Fallback to sample books only if CloudFront book not found
  return sampleBooks.find(b => b.id === bookId) || null;
};
